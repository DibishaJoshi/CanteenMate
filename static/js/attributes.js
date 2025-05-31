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
            <input type="text" name="value_name[]" placeholder="Value name">
            <input type="number" name="price_adjustment[]" placeholder="Price adjustment" min="0" step="0.01">
            <button type="button" class="btn-remove"><i class="fas fa-minus"></i></button>
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

// Edit attribute
document.querySelectorAll('.btn-edit').forEach(btn => {
    btn.addEventListener('click', () => {
        const modal = document.getElementById('attributeModal');
        const form = document.getElementById('attributeForm');

        // Get values from data attributes
        const id = btn.dataset.id;
        const name = btn.dataset.name;
        const status = btn.dataset.status;
        const valuesCount = parseInt(btn.dataset.valuesCount);
        
        const nameInput = document.getElementById('attributeName');
        const idInput = document.getElementById('attributeId');
        const valueContainer = document.querySelector('.attribute-values');

        // Set form action if needed (optional if using one POST route for both)
        // form.action = `/edit_attribute/${id}`; // Only if using separate route

        // Set field values
        idInput.value = id;
        nameInput.value = name;
        document.querySelector(`input[name="status"][value="${status}"]`).checked = true;

        // Clear current value rows
        valueContainer.innerHTML = '';

        for (let i = 0; i < valuesCount; i++) {
            const value = btn.dataset[`value${i}`];
            const price = btn.dataset[`price${i}`];

            const row = document.createElement('div');
            row.classList.add('attribute-value-row');
            row.innerHTML = `
                <input type="text" name="value_name[]" value="${value}" placeholder="Value name">
                <input type="number" name="price_adjustment[]" value="${price}" placeholder="Price adjustment" min="0" step="0.01">
                <button type="button" class="btn-remove"><i class="fas fa-minus"></i></button>
            `;
            valueContainer.appendChild(row);
        }

        modal.style.display = 'block';
    });
});

    console.log('attributes.js loaded');
});