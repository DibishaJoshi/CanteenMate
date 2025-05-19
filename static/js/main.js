// Main JavaScript for Canteen Management System

document.addEventListener('DOMContentLoaded', function() {
    // Toggle sidebar on mobile
    const navToggle = document.querySelector('.nav-toggle');
    const sidebar = document.querySelector('.sidebar');
    
    if (navToggle && sidebar) {
        navToggle.addEventListener('click', function() {
            sidebar.classList.toggle('active');
        });
    }
    
    // Submenu toggle
    const submenuItems = document.querySelectorAll('.menu-item.has-submenu');
    
    submenuItems.forEach(item => {
        item.addEventListener('click', function(e) {
            if (e.target === item || e.target.parentElement === item) {
                e.preventDefault();
                this.classList.toggle('open');
            }
        });
    });
    
    // Category pills selection
    const categoryPills = document.querySelectorAll('.category-pill');
    
    categoryPills.forEach(pill => {
        pill.addEventListener('click', function() {
            categoryPills.forEach(p => p.classList.remove('active'));
            this.classList.add('active');
            
            // Here you would add code to filter menu items by category
        });
    });
    
    // Quantity buttons in order
    const quantityBtns = document.querySelectorAll('.order-item-quantity button');
    
    quantityBtns.forEach(btn => {
        btn.addEventListener('click', function() {
            const input = this.parentElement.querySelector('span');
            let value = parseInt(input.textContent);
            
            if (this.classList.contains('decrease')) {
                if (value > 1) value--;
            } else {
                value++;
            }
            
            input.textContent = value;
            updateOrderSummary();
        });
    });
    
    // Remove item from order
    const removeButtons = document.querySelectorAll('.order-item-remove');
    
    removeButtons.forEach(btn => {
        btn.addEventListener('click', function() {
            this.closest('.order-item').remove();
            updateOrderSummary();
        });
    });
    
    // Update order summary
    function updateOrderSummary() {
        // This is a placeholder for the calculation logic
        // In a real app, you would calculate the total based on items and quantities
        let subtotal = 0;
        const orderItems = document.querySelectorAll('.order-item');
        
        orderItems.forEach(item => {
            const price = parseFloat(item.querySelector('.order-item-price').textContent.replace('Rs. ', ''));
            const quantity = parseInt(item.querySelector('.order-item-quantity span').textContent);
            subtotal += price * quantity;
        });
        
        // Update UI
        const subtotalEl = document.querySelector('.summary-item.subtotal .value');
        const taxEl = document.querySelector('.summary-item.tax .value');
        const discountEl = document.querySelector('.summary-item.discount .value');
        const totalEl = document.querySelector('.summary-item.total .value');
        
        if (subtotalEl) subtotalEl.textContent = 'Rs. ' + subtotal.toFixed(2);
        
        // Calculate tax (10% for example)
        const tax = subtotal * 0.1;
        if (taxEl) taxEl.textContent = 'Rs. ' + tax.toFixed(2);
        
        // Calculate discount if any
        const discount = 0; // placeholder
        if (discountEl) discountEl.textContent = 'Rs. ' + discount.toFixed(2);
        
        // Calculate total
        const total = subtotal + tax - discount;
        if (totalEl) totalEl.textContent = 'Rs. ' + total.toFixed(2);
    }
    
    // Payment method selection
    const paymentOptions = document.querySelectorAll('.payment-option');
    
    paymentOptions.forEach(option => {
        option.addEventListener('click', function() {
            paymentOptions.forEach(o => o.classList.remove('active'));
            this.classList.add('active');
            
            // Update hidden input for form submission
            const paymentMethod = this.getAttribute('data-method');
            document.querySelector('input[name="payment_method"]').value = paymentMethod;
        });
    });
    
    // Form validation (using Bootstrap validation)
    const forms = document.querySelectorAll('.needs-validation');
    
    Array.from(forms).forEach(form => {
        form.addEventListener('submit', event => {
            if (!form.checkValidity()) {
                event.preventDefault();
                event.stopPropagation();
            }
            
            form.classList.add('was-validated');
        }, false);
    });
    
    // Initialize any Bootstrap tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function(tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
    
    // Initialize any Bootstrap popovers
    const popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    popoverTriggerList.map(function(popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });
});