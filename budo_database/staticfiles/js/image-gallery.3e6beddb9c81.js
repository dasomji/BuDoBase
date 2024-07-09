document.addEventListener('DOMContentLoaded', function () {
    const modal = document.getElementById('fullscreen-modal');
    const modalImg = document.getElementById('fullscreen-image');
    const closeBtn = document.getElementsByClassName('close-modal')[0];
    const prevBtn = document.querySelector('.nav-button.prev');
    const nextBtn = document.querySelector('.nav-button.next');
    const galleryItems = document.querySelectorAll('.gallery-item');
    let currentIndex = 0;

    function openModal(index) {
        modal.style.display = 'block';
        modalImg.src = galleryItems[index].querySelector('img').src;
        currentIndex = index;
    }

    function closeModal() {
        modal.style.display = 'none';
    }

    function showNextImage() {
        currentIndex = (currentIndex + 1) % galleryItems.length;
        modalImg.src = galleryItems[currentIndex].querySelector('img').src;
    }

    function showPrevImage() {
        currentIndex = (currentIndex - 1 + galleryItems.length) % galleryItems.length;
        modalImg.src = galleryItems[currentIndex].querySelector('img').src;
    }

    galleryItems.forEach((item, index) => {
        item.addEventListener('click', () => openModal(index));
    });

    closeBtn.addEventListener('click', closeModal);
    prevBtn.addEventListener('click', showPrevImage);
    nextBtn.addEventListener('click', showNextImage);

    // Close modal when clicking outside the image
    modal.addEventListener('click', function (event) {
        if (event.target === modal) {
            closeModal();
        }
    });

    // Keyboard navigation
    document.addEventListener('keydown', function (event) {
        if (modal.style.display === 'block') {
            if (event.key === 'ArrowLeft') {
                showPrevImage();
            } else if (event.key === 'ArrowRight') {
                showNextImage();
            } else if (event.key === 'Escape') {
                closeModal();
            }
        }
    });

    // Swipe functionality
    let touchStartX = 0;
    let touchEndX = 0;

    modal.addEventListener('touchstart', function (event) {
        touchStartX = event.changedTouches[0].screenX;
    }, false);

    modal.addEventListener('touchend', function (event) {
        touchEndX = event.changedTouches[0].screenX;
        handleSwipe();
    }, false);

    function handleSwipe() {
        if (touchEndX < touchStartX) {
            showNextImage();
        }
        if (touchEndX > touchStartX) {
            showPrevImage();
        }
    }
});