// This Script allows to sort tables and filter by budo_family.

(function() {
    'use strict';
    
    let isInitialized = false;
    
    // Configuration
    const CONFIG = {
        tableSelector: 'table',
        headerSelector: 'th',
        rowSelector: 'tr:nth-child(n+2)',
        budoFamilySelector: '.budo_family',
        tableRowSelector: '.table_row'
    };
    
    // Utility functions
    function debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }
    
    // Function to get the text content of a cell
    function getCellValue(row, columnIdx) {
        if (!row || !row.children || !row.children[columnIdx]) {
            return '';
        }
        
        const cell = row.children[columnIdx];
        
        // Check for data-sort attribute first (for proper sorting of dates, etc.)
        if (cell.dataset && cell.dataset.sort) {
            return cell.dataset.sort;
        }
        
        // Handle special toggle switches
        if (cell.classList.contains('zug-toggle')) {
            const switchElement = cell.querySelector('.switch');
            return switchElement && switchElement.classList.contains('ja') ? 'ja' : 'nein';
        }
        
        return cell.innerText || cell.textContent || '';
    }
    
    // Function to compare two rows based on the text content of a specific column
    function rowComparer(columnIdx, ascending) {
        return function (rowA, rowB) {
            const cellValueA = getCellValue(ascending ? rowA : rowB, columnIdx);
            const cellValueB = getCellValue(ascending ? rowB : rowA, columnIdx);
            
            // If the cell values are numeric, compare them as numbers
            if (cellValueA !== '' && cellValueB !== '' && !isNaN(cellValueA) && !isNaN(cellValueB)) {
                return parseFloat(cellValueA) - parseFloat(cellValueB);
            } else {
                // Otherwise, compare them as strings
                return cellValueA.toString().localeCompare(cellValueB, undefined, {
                    numeric: true,
                    sensitivity: 'base'
                });
            }
        };
    }
    
    // Table sorting functionality
    function initTableSorting() {
        // Use event delegation to handle clicks on table headers
        document.addEventListener('click', function(event) {
            const tableHeader = event.target.closest(CONFIG.headerSelector);
            if (!tableHeader) return;
            
            const table = tableHeader.closest(CONFIG.tableSelector);
            if (!table) return;
            
            // Prevent default behavior
            event.preventDefault();
            
            // Get the index of this header in the row
            const headerIdx = Array.from(tableHeader.parentNode.children).indexOf(tableHeader);
            
            // Get all the rows of the table, except for the first one (the header row)
            const rows = Array.from(table.querySelectorAll(CONFIG.rowSelector));
            
            if (rows.length === 0) return;
            
            // Toggle sort direction
            const currentAscending = tableHeader.dataset.ascending === 'true';
            tableHeader.dataset.ascending = !currentAscending;
            
            // Clear other headers' sort indicators
            table.querySelectorAll(CONFIG.headerSelector).forEach(th => {
                if (th !== tableHeader) {
                    delete th.dataset.ascending;
                }
            });
            
            // Sort the rows
            const sortedRows = rows.sort(rowComparer(headerIdx, !currentAscending));
            
            // Create document fragment for better performance
            const fragment = document.createDocumentFragment();
            sortedRows.forEach(row => fragment.appendChild(row));
            
            // Append sorted rows back to the table
            table.appendChild(fragment);
        });
    }
    
    // Budo family filtering functionality
    function initBudoFamilyFiltering() {
        // Use event delegation for budo_family clicks
        document.addEventListener('click', function(event) {
            const budoFamilyCell = event.target.closest(CONFIG.budoFamilySelector);
            if (!budoFamilyCell) return;
            
            // Prevent default behavior
            event.preventDefault();
            
            const clickedValue = budoFamilyCell.textContent.trim();
            if (!clickedValue) return;
            
            filterByBudoFamily(clickedValue);
        });
    }
    
    // Filter table rows by budo family
    function filterByBudoFamily(familyValue) {
        const allRows = document.querySelectorAll(CONFIG.tableRowSelector);
        
        allRows.forEach(row => {
            const budoFamilyCell = row.querySelector(CONFIG.budoFamilySelector);
            if (!budoFamilyCell) {
                row.style.display = 'none';
                return;
            }
            
            const rowFamilyValue = budoFamilyCell.textContent.trim();
            if (rowFamilyValue === familyValue) {
                row.style.display = '';
            } else {
                row.style.display = 'none';
            }
        });
        
        // Add visual feedback
        addFilterFeedback(familyValue);
    }
    
    // Add visual feedback for active filter
    function addFilterFeedback(familyValue) {
        // Remove existing filter feedback
        const existingFeedback = document.querySelector('.filter-feedback');
        if (existingFeedback) {
            existingFeedback.remove();
        }
        
        // Create new filter feedback
        const feedback = document.createElement('div');
        feedback.className = 'filter-feedback';
        feedback.innerHTML = `
            <span>Filtered by: <strong>${familyValue}</strong></span>
            <button type="button" class="clear-filter-btn" title="Clear filter">×</button>
        `;
        feedback.style.cssText = `
            position: sticky;
            top: 0;
            background: #ffeb3b;
            padding: 8px 16px;
            border: 1px solid #fdd835;
            border-radius: 4px;
            margin-bottom: 8px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            z-index: 10;
        `;
        
        // Add clear filter functionality
        const clearBtn = feedback.querySelector('.clear-filter-btn');
        clearBtn.style.cssText = `
            background: none;
            border: none;
            font-size: 18px;
            cursor: pointer;
            padding: 0 4px;
        `;
        
        clearBtn.addEventListener('click', clearFilter);
        
        // Insert feedback before the first table
        const firstTable = document.querySelector(CONFIG.tableSelector);
        if (firstTable) {
            firstTable.parentNode.insertBefore(feedback, firstTable);
        }
    }
    
    // Clear family filter
    function clearFilter() {
        const allRows = document.querySelectorAll(CONFIG.tableRowSelector);
        allRows.forEach(row => {
            row.style.display = '';
        });
        
        const feedback = document.querySelector('.filter-feedback');
        if (feedback) {
            feedback.remove();
        }
    }
    
    // Add double-click to clear filter functionality
    function initDoubleClickClear() {
        document.addEventListener('dblclick', function(event) {
            const budoFamilyCell = event.target.closest(CONFIG.budoFamilySelector);
            if (budoFamilyCell) {
                event.preventDefault();
                clearFilter();
            }
        });
    }
    
    // Add keyboard support
    function initKeyboardSupport() {
        document.addEventListener('keydown', function(event) {
            // Clear filter with Escape key
            if (event.key === 'Escape') {
                const feedback = document.querySelector('.filter-feedback');
                if (feedback) {
                    clearFilter();
                }
            }
        });
    }
    
    // Wait for dependencies and DOM
    function waitForReady() {
        const checkReady = () => {
            const domReady = document.readyState === 'complete' || document.readyState === 'interactive';
            
            if (domReady && !isInitialized) {
                init();
            } else if (!isInitialized) {
                setTimeout(checkReady, 50);
            }
        };
        
        checkReady();
    }
    
    // Initialize all functionality
    function init() {
        if (isInitialized) return;
        
        try {
            initTableSorting();
            initBudoFamilyFiltering();
            initDoubleClickClear();
            initKeyboardSupport();
            
            isInitialized = true;
            console.log('Table filtering and sorting initialized successfully');
            
        } catch (error) {
            console.error('Error initializing table functionality:', error);
        }
    }
    
    // Start initialization
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', waitForReady);
    } else {
        waitForReady();
    }
    
    // Expose functions for debugging
    window.tableUtils = {
        clearFilter,
        filterByBudoFamily
    };
    
})();