(function() {
    'use strict';
    
    // Configuration
    const CONFIG = {
        cookieName: 'closedCards',
        cookieExpireDays: 30,
        animationDuration: 300,
        mobileBreakpoint: 1024
    };
    
    // State management
    let isInitialized = false;
    let closedCards = new Set();
    
    // Utility functions
    const utils = {
        // Improved mobile detection
        isMobileOrTablet() {
            // Check both user agent and screen size
            const userAgentCheck = /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent);
            const screenSizeCheck = window.innerWidth <= CONFIG.mobileBreakpoint;
            const touchSupport = 'ontouchstart' in window || navigator.maxTouchPoints > 0;
            
            return userAgentCheck || (screenSizeCheck && touchSupport);
        },
        
        // Safe cookie operations with error handling
        getCookie(name) {
            try {
                if (typeof Cookies === 'undefined') {
                    console.warn('js-cookie library not loaded, falling back to document.cookie');
                    const value = `; ${document.cookie}`;
                    const parts = value.split(`; ${name}=`);
                    if (parts.length === 2) {
                        return parts.pop().split(';').shift();
                    }
                    return null;
                }
                return Cookies.get(name);
            } catch (error) {
                console.warn('Error reading cookie:', error);
                return null;
            }
        },
        
        setCookie(name, value) {
            try {
                if (typeof Cookies === 'undefined') {
                    console.warn('js-cookie library not loaded, falling back to document.cookie');
                    const expires = new Date();
                    expires.setTime(expires.getTime() + (CONFIG.cookieExpireDays * 24 * 60 * 60 * 1000));
                    document.cookie = `${name}=${value}; expires=${expires.toUTCString()}; path=/`;
                    return;
                }
                Cookies.set(name, value, { expires: CONFIG.cookieExpireDays });
            } catch (error) {
                console.warn('Error setting cookie:', error);
            }
        },
        
        // Safe JSON operations
        parseJSON(jsonString) {
            try {
                return JSON.parse(jsonString);
            } catch (error) {
                console.warn('Error parsing JSON:', error);
                return null;
            }
        },
        
        // Debounce function to prevent rapid cookie updates
        debounce(func, wait) {
            let timeout;
            return function executedFunction(...args) {
                const later = () => {
                    clearTimeout(timeout);
                    func(...args);
                };
                clearTimeout(timeout);
                timeout = setTimeout(later, wait);
            };
        },
        
        // Check if element exists and is visible
        isElementValid(element) {
            return element && element.offsetParent !== null;
        }
    };
    
    // Card management functions
    const cardManager = {
        // Get all cards safely
        getAllCards() {
            return Array.from(document.querySelectorAll('.card')).filter(card => 
                card.id && utils.isElementValid(card)
            );
        },
        
        // Get card components safely
        getCardComponents(card) {
            const header = card.querySelector('.info-header-container');
            const content = card.querySelector('.card-info-container');
            
            if (!header || !content) {
                console.warn('Card missing required components:', card.id);
                return null;
            }
            
            return { header, content };
        },
        
        // Close a card
        closeCard(card, animate = true) {
            const components = this.getCardComponents(card);
            if (!components) return false;
            
            const { content } = components;
            
            card.classList.add('closed-card');
            closedCards.add(card.id);
            
            if (animate && window.jQuery) {
                window.jQuery(content).slideUp(CONFIG.animationDuration);
            } else {
                content.style.display = 'none';
            }
            
            return true;
        },
        
        // Open a card
        openCard(card, animate = true) {
            const components = this.getCardComponents(card);
            if (!components) return false;
            
            const { content } = components;
            
            card.classList.remove('closed-card');
            closedCards.delete(card.id);
            
            if (animate && window.jQuery) {
                window.jQuery(content).slideDown(CONFIG.animationDuration);
            } else {
                content.style.display = 'block';
            }
            
            return true;
        },
        
        // Toggle a card
        toggleCard(card) {
            if (card.classList.contains('closed-card')) {
                return this.openCard(card);
            } else {
                return this.closeCard(card);
            }
        },
        
        // Save state to cookie (debounced)
        saveState: utils.debounce(() => {
            const cardsArray = Array.from(closedCards);
            utils.setCookie(CONFIG.cookieName, JSON.stringify(cardsArray));
        }, 250),
        
        // Load state from cookie
        loadState() {
            const cookieValue = utils.getCookie(CONFIG.cookieName);
            if (!cookieValue) return;
            
            const savedCards = utils.parseJSON(cookieValue);
            if (!Array.isArray(savedCards)) return;
            
            closedCards = new Set(savedCards);
            
            // Apply saved state
            savedCards.forEach(cardId => {
                const card = document.getElementById(cardId);
                if (card) {
                    this.closeCard(card, false);
                }
            });
        },
        
        // Initialize default state for mobile
        initializeMobileState() {
            if (!utils.isMobileOrTablet()) return;
            
            // Only close cards if no saved state exists
            const cookieValue = utils.getCookie(CONFIG.cookieName);
            if (cookieValue) return;
            
            const cards = this.getAllCards();
            cards.forEach(card => {
                this.closeCard(card, false);
            });
            
            this.saveState();
        },
        
        // Show open cards
        showOpenCards() {
            const cards = this.getAllCards();
            cards.forEach(card => {
                if (!card.classList.contains('closed-card')) {
                    const components = this.getCardComponents(card);
                    if (components) {
                        components.content.style.display = 'block';
                    }
                }
            });
        }
    };
    
    // Toggle button management
    const toggleButton = {
        create() {
            const cards = cardManager.getAllCards();
            if (cards.length <= 1) return;
            
            // Remove existing button
            const existingButton = document.getElementById('toggle-all');
            if (existingButton) {
                existingButton.remove();
            }
            
            const button = document.createElement('div');
            button.id = 'toggle-all';
            button.className = 'toggle-all-button button';
            button.textContent = 'Toggle cards';
            button.setAttribute('role', 'button');
            button.setAttribute('tabindex', '0');
            
            // Check if interaction bar exists
            if (!document.getElementById('interaction-bar')) {
                button.classList.add('no-bar');
            }
            
            // Add click and keyboard event listeners
            const handleToggle = (event) => {
                if (event.type === 'keydown' && event.key !== 'Enter' && event.key !== ' ') {
                    return;
                }
                event.preventDefault();
                this.toggleAll();
            };
            
            button.addEventListener('click', handleToggle);
            button.addEventListener('keydown', handleToggle);
            
            document.body.appendChild(button);
        },
        
        toggleAll() {
            const cards = cardManager.getAllCards();
            if (cards.length === 0) return;
            
            const allClosed = cards.every(card => card.classList.contains('closed-card'));
            
            cards.forEach(card => {
                if (allClosed) {
                    cardManager.openCard(card);
                } else {
                    cardManager.closeCard(card);
                }
            });
            
            cardManager.saveState();
        }
    };
    
    // Event handling
    const eventHandler = {
        // Set up event delegation for card headers
        setupCardEvents() {
            // Remove existing listeners to prevent duplicates
            document.removeEventListener('click', this.handleCardClick);
            document.removeEventListener('keydown', this.handleCardKeydown);
            
            // Use event delegation for better performance and dynamic content support
            document.addEventListener('click', this.handleCardClick);
            document.addEventListener('keydown', this.handleCardKeydown);
        },
        
        handleCardClick(event) {
            const header = event.target.closest('.info-header-container');
            if (!header) return;
            
            const card = header.closest('.card');
            if (!card || !card.id) return;
            
            event.preventDefault();
            cardManager.toggleCard(card);
            cardManager.saveState();
        },
        
        handleCardKeydown(event) {
            if (event.key !== 'Enter' && event.key !== ' ') return;
            
            const header = event.target.closest('.info-header-container');
            if (!header) return;
            
            const card = header.closest('.card');
            if (!card || !card.id) return;
            
            event.preventDefault();
            cardManager.toggleCard(card);
            cardManager.saveState();
        },
        
        // Handle orientation and resize changes
        setupResponsiveEvents() {
            let resizeTimeout;
            const handleResize = () => {
                clearTimeout(resizeTimeout);
                resizeTimeout = setTimeout(() => {
                    // Re-check mobile state on orientation change
                    if (!isInitialized) return;
                    
                    // Only auto-close on mobile if no user preferences exist
                    const cookieValue = utils.getCookie(CONFIG.cookieName);
                    if (!cookieValue && utils.isMobileOrTablet()) {
                        cardManager.initializeMobileState();
                    }
                }, 250);
            };
            
            window.addEventListener('resize', handleResize);
            window.addEventListener('orientationchange', handleResize);
        }
    };
    
    // Initialization
    function init() {
        if (isInitialized) return;
        
        try {
            // Load saved state first
            cardManager.loadState();
            
            // Initialize mobile state if needed
            cardManager.initializeMobileState();
            
            // Show open cards
            cardManager.showOpenCards();
            
            // Set up event listeners
            eventHandler.setupCardEvents();
            eventHandler.setupResponsiveEvents();
            
            // Create toggle button
            toggleButton.create();
            
            isInitialized = true;
            console.log('Card functionality initialized successfully');
            
        } catch (error) {
            console.error('Error initializing card functionality:', error);
        }
    }
    
    // Wait for DOM and dependencies
    function waitForDependencies() {
        const checkReady = () => {
            const domReady = document.readyState === 'complete' || document.readyState === 'interactive';
            const jqueryReady = typeof window.jQuery !== 'undefined';
            
            if (domReady) {
                // Don't wait for jQuery if it's not loaded within 2 seconds
                setTimeout(() => {
                    if (!isInitialized) {
                        init();
                    }
                }, 100);
                
                if (jqueryReady) {
                    window.jQuery(document).ready(init);
                } else {
                    init();
                }
            } else {
                setTimeout(checkReady, 50);
            }
        };
        
        checkReady();
    }
    
    // Start the initialization process
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', waitForDependencies);
    } else {
        waitForDependencies();
    }
    
    // Expose public API for debugging
    window.CardFunctionality = {
        init,
        utils,
        cardManager,
        toggleButton,
        isInitialized: () => isInitialized,
        getClosedCards: () => Array.from(closedCards)
    };
    
})();
