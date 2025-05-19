// Wait for DOM to load
document.addEventListener('DOMContentLoaded', () => {

    // Day tabs switching
    const dayTabs = document.querySelectorAll('.day-tab');
    dayTabs.forEach(tab => {
        tab.addEventListener('click', () => {
            document.querySelector('.day-tab.active')?.classList.remove('active');
            tab.classList.add('active');
            // Load data for selected day (AJAX/Fetch can be used here)
            console.log(`Switched to ${tab.dataset.day}`);
        });
    });

    // Modal elements
    const modal = document.getElementById('menu-modal');
    const openModalBtn = document.getElementById('add-menu-btn');
    const closeModalBtn = modal.querySelector('.close');
    const cancelBtn = modal.querySelector('.cancel-btn');
    const saveBtn = modal.querySelector('.save-btn');

    // Open modal
    openModalBtn.addEventListener('click', () => {
        modal.style.display = 'block';
    });

    // Close modal (X or Cancel)
    closeModalBtn.addEventListener('click', () => {
        modal.style.display = 'none';
    });

    cancelBtn.addEventListener('click', () => {
        modal.style.display = 'none';
    });

    // Save selected items to menu (basic simulation)
    saveBtn.addEventListener('click', () => {
        const checkedItems = modal.querySelectorAll('.item-checkbox input:checked');
        const selectedItems = Array.from(checkedItems).map(cb => cb.nextElementSibling.textContent.trim());
        
        if (selectedItems.length > 0) {
            alert(`Added to menu:\n${selectedItems.join('\n')}`);
        } else {
            alert("No items selected.");
        }
        modal.style.display = 'none';
    });

    // Remove item
    const removeButtons = document.querySelectorAll('.remove-item');
    removeButtons.forEach(btn => {
        btn.addEventListener('click', () => {
            const confirmRemove = confirm("Are you sure you want to remove this item?");
            if (confirmRemove) {
                const item = btn.closest('.menu-item');
                item.remove();
            }
        });
    });

    // Search menu
    const searchInput = document.getElementById('search-menu');
    const searchBtn = document.querySelector('.search-btn');

    const filterMenus = () => {
        const query = searchInput.value.toLowerCase();
        const items = document.querySelectorAll('.menu-item');

        items.forEach(item => {
            const text = item.innerText.toLowerCase();
            if (text.includes(query)) {
                item.style.display = '';
            } else {
                item.style.display = 'none';
            }
        });
    };

    searchBtn.addEventListener('click', filterMenus);
    searchInput.addEventListener('keyup', (e) => {
        if (e.key === 'Enter') filterMenus();
    });

    // Close modal if clicked outside
    window.addEventListener('click', (e) => {
        if (e.target === modal) {
            modal.style.display = 'none';
        }
    });
});
