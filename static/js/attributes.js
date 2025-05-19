document.addEventListener('DOMContentLoaded', function () {
    const modal = document.getElementById('attributeModal');
    const openModalBtn = document.querySelector('.add-btn');
    const closeModalBtn = document.querySelector('.close-btn');
    const cancelBtn = document.getElementById('cancelBtn');
    const addValueBtn = document.querySelector('.btn-add-value');
    const attributeValues = document.querySelector('.attribute-values');

    // Open modal
    openModalBtn.addEventListener('click', () => {
        modal.style.display = 'block';
    });

    // Close modal
    function closeModal() {
        modal.style.display = 'none';
    }

    closeModalBtn.addEventListener('click', closeModal);
    cancelBtn.addEventListener('click', closeModal);

    // Add new attribute value row
    addValueBtn.addEventListener('click', () => {
        const newRow = document.createElement('div');
        newRow.classList.add('attribute-value-row');
        newRow.innerHTML = `
            <input type="text" placeholder="Value name">
            <input type="number" placeholder="Price adjustment" min="0" step="0.01">
            <button type="button" class="btn-remove"><i class="icon-minus"></i></button>
        `;
        attributeValues.appendChild(newRow);
    });

    // Event delegation for removing value rows
    attributeValues.addEventListener('click', function (e) {
        if (e.target.closest('.btn-remove')) {
            const row = e.target.closest('.attribute-value-row');
            if (row) row.remove();
        }
    });

    // Close modal if clicked outside
    window.addEventListener('click', (e) => {
        if (e.target === modal) {
            closeModal();
        }
    });

    // Search functionality
    const searchInput = document.querySelector('.search-box input');
    const tableRows = document.querySelectorAll('.attributes-list table tbody tr');

    searchInput.addEventListener('keyup', () => {
        const term = searchInput.value.toLowerCase();
        tableRows.forEach(row => {
            const text = row.textContent.toLowerCase();
            row.style.display = text.includes(term) ? '' : 'none';
        });
    });

    console.log('✅ attributes.js loaded');
});
