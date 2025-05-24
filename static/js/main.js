function toggleDropdown() {
    document.getElementById("notificationDropdown").classList.toggle("show");
}

// Close dropdown when clicking outside
document.addEventListener("click", function(e) {
    if (!e.target.closest(".notifications")) {
        document.getElementById("notificationDropdown").classList.remove("show");
    }
});

// Fetch notifications from Flask endpoint
function fetchNotifications() {
    $.getJSON("/notifications", function(data) {
        const dropdown = $("#notificationDropdown");
        const badge = $("#notif-badge");
        dropdown.empty();

        if (data.length === 0) {
            dropdown.append('<div class="notification-item">No notifications</div>');
        } else {
            data.forEach(item => {
                dropdown.append(`<div class="notification-item"><div>${item.message}</div>
                                    <small style="color: gray;">${item.time}</small></div>`);
                                });
        }

        // Update badge
        badge.text(data.length);
        badge.css("display", data.length > 0 ? "inline-block" : "none");
    });
}

// Main JavaScript for Canteen Management System

// document.addEventListener('DOMContentLoaded', function() {
//     // Toggle sidebar on mobile
//     const navToggle = document.querySelector('.nav-toggle');
//     const sidebar = document.querySelector('.sidebar');
    
//     if (navToggle && sidebar) {
//         navToggle.addEventListener('click', function() {
//             sidebar.classList.toggle('active');
//         });
//     }
    
//     // Submenu toggle
//     const submenuItems = document.querySelectorAll('.menu-item.has-submenu');
    
//     submenuItems.forEach(item => {
//         item.addEventListener('click', function(e) {
//             if (e.target === item || e.target.parentElement === item) {
//                 e.preventDefault();
//                 this.classList.toggle('open');
//             }
//         });
//     });
    
//     // Category pills selection
//     const categoryPills = document.querySelectorAll('.category-pill');
    
//     categoryPills.forEach(pill => {
//         pill.addEventListener('click', function() {
//             categoryPills.forEach(p => p.classList.remove('active'));
//             this.classList.add('active');
            
//             // Here you would add code to filter menu items by category
//         });
//     });
    
//     // Quantity buttons in order
//     const quantityBtns = document.querySelectorAll('.order-item-quantity button');
    
//     quantityBtns.forEach(btn => {
//         btn.addEventListener('click', function() {
//             const input = this.parentElement.querySelector('span');
//             let value = parseInt(input.textContent);
            
//             if (this.classList.contains('decrease')) {
//                 if (value > 1) value--;
//             } else {
//                 value++;
//             }
            
//             input.textContent = value;
//             updateOrderSummary();
//         });
//     });
    
//     // Remove item from order
//     const removeButtons = document.querySelectorAll('.order-item-remove');
    
//     removeButtons.forEach(btn => {
//         btn.addEventListener('click', function() {
//             this.closest('.order-item').remove();
//             updateOrderSummary();
//         });
//     });
    
//     // Update order summary
//     function updateOrderSummary() {
//         // This is a placeholder for the calculation logic
//         // In a real app, you would calculate the total based on items and quantities
//         let subtotal = 0;
//         const orderItems = document.querySelectorAll('.order-item');
        
//         orderItems.forEach(item => {
//             const price = parseFloat(item.querySelector('.order-item-price').textContent.replace('Rs. ', ''));
//             const quantity = parseInt(item.querySelector('.order-item-quantity span').textContent);
//             subtotal += price * quantity;
//         });
        
//         // Update UI
//         const subtotalEl = document.querySelector('.summary-item.subtotal .value');
//         const taxEl = document.querySelector('.summary-item.tax .value');
//         const discountEl = document.querySelector('.summary-item.discount .value');
//         const totalEl = document.querySelector('.summary-item.total .value');
        
//         if (subtotalEl) subtotalEl.textContent = 'Rs. ' + subtotal.toFixed(2);
        
//         // Calculate tax (10% for example)
//         const tax = subtotal * 0.1;
//         if (taxEl) taxEl.textContent = 'Rs. ' + tax.toFixed(2);
        
//         // Calculate discount if any
//         const discount = 0; // placeholder
//         if (discountEl) discountEl.textContent = 'Rs. ' + discount.toFixed(2);
        
//         // Calculate total
//         const total = subtotal + tax - discount;
//         if (totalEl) totalEl.textContent = 'Rs. ' + total.toFixed(2);
//     }
    
//     // Payment method selection
//     const paymentOptions = document.querySelectorAll('.payment-option');
    
//     paymentOptions.forEach(option => {
//         option.addEventListener('click', function() {
//             paymentOptions.forEach(o => o.classList.remove('active'));
//             this.classList.add('active');
            
//             // Update hidden input for form submission
//             const paymentMethod = this.getAttribute('data-method');
//             document.querySelector('input[name="payment_method"]').value = paymentMethod;
//         });
//     });
    
//     // Form validation (using Bootstrap validation)
//     const forms = document.querySelectorAll('.needs-validation');
    
//     Array.from(forms).forEach(form => {
//         form.addEventListener('submit', event => {
//             if (!form.checkValidity()) {
//                 event.preventDefault();
//                 event.stopPropagation();
//             }
            
//             form.classList.add('was-validated');
//         }, false);
//     });
    
//     // Initialize any Bootstrap tooltips
//     const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
//     tooltipTriggerList.map(function(tooltipTriggerEl) {
//         return new bootstrap.Tooltip(tooltipTriggerEl);
//     });
    
//     // Initialize any Bootstrap popovers
//     const popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
//     popoverTriggerList.map(function(popoverTriggerEl) {
//         return new bootstrap.Popover(popoverTriggerEl);
//     });
// });




// //user
// // JavaScript for the CanteenMate System
//         document.addEventListener('DOMContentLoaded', function() {
//             // Navigation Functions
//             const menuItems = document.querySelectorAll('.menu-item');
//             const pages = document.querySelectorAll('.page');
//             const pageTitle = document.querySelector('.page-title');
            
//             // Function to navigate between pages
//             function navigateToPage(pageName) {
//                 // Hide all pages
//                 pages.forEach(page => {
//                     page.classList.remove('active');
//                 });
                
//                 // Show selected page
//                 const selectedPage = document.getElementById(pageName);
//                 if (selectedPage) {
//                     selectedPage.classList.add('active');
//                 }
                
//                 // Update active menu item
//                 menuItems.forEach(item => {
//                     item.classList.remove('active');
//                     if (item.dataset.page === pageName) {
//                         item.classList.add('active');
//                     }
//                 });
                
//                 // Update page title
//                 if (pageTitle) {
//                     pageTitle.textContent = pageName.charAt(0).toUpperCase() + pageName.slice(1);
//                 }
//             }
            
//             // Add click event listeners to menu items
//             menuItems.forEach(item => {
//                 item.addEventListener('click', function(e) {
//                     e.preventDefault();
//                     const pageName = this.dataset.page;
//                     navigateToPage(pageName);
//                     // Update URL hash
//                     window.location.hash = pageName;
//                 });
//             });
            
//             // Check URL hash on page load
//             const checkHash = () => {
//                 const hash = window.location.hash.substring(1);
//                 if (hash && document.getElementById(hash)) {
//                     navigateToPage(hash);
//                 }
//             };
            
//             // Initialize hash check
//             checkHash();
            
//             // Listen for hash changes
//             window.addEventListener('hashchange', checkHash);
            
//             // Tab functionality for profile page
//             const tabButtons = document.querySelectorAll('.tab-btn');
            
//             tabButtons.forEach(button => {
//                 button.addEventListener('click', function() {
//                     // Remove active class from all tab buttons
//                     tabButtons.forEach(btn => btn.classList.remove('active'));
                    
//                     // Add active class to clicked button
//                     this.classList.add('active');
                    
//                     // Get tab content id
//                     const tabId = this.dataset.tab;
                    
//                     // Hide all tab panes
//                     document.querySelectorAll('.tab-pane').forEach(pane => {
//                         pane.classList.remove('active');
//                     });
                    
//                     // Show selected tab pane
//                     const selectedPane = document.getElementById(tabId);
//                     if (selectedPane) {
//                         selectedPane.classList.add('active');
//                     }
//                 });
//             });
            
//             // Cart functionality
//             const quantityButtons = document.querySelectorAll('.quantity-btn');
            
//             quantityButtons.forEach(button => {
//                 button.addEventListener('click', function() {
//                     const isIncrement = this.textContent === '+';
//                     const quantityElement = this.parentElement.querySelector('.quantity-value');
//                     let quantity = parseInt(quantityElement.textContent);
                    
//                     if (isIncrement) {
//                         quantity++;
//                     } else if (quantity > 1) {
//                         quantity--;
//                     }
                    
//                     quantityElement.textContent = quantity;
//                     updateCartTotals();
//                 });
//             });
            
//             // Remove item from cart
//             const removeButtons = document.querySelectorAll('.remove-item');
            
//             removeButtons.forEach(button => {
//                 button.addEventListener('click', function() {
//                     const cartItem = this.closest('.cart-item');
//                     cartItem.style.opacity = '0';
//                     setTimeout(() => {
//                         cartItem.remove();
//                         updateCartTotals();
//                     }, 300);
//                 });
//             });
            
//             // Add to cart functionality
//             const addToCartButtons = document.querySelectorAll('.add-to-cart');
            
//             addToCartButtons.forEach(button => {
//                 button.addEventListener('click', function() {
//                     // Animation for button
//                     this.textContent = 'Added!';
//                     this.style.backgroundColor = '#34A853';
                    
//                     setTimeout(() => {
//                         this.textContent = 'Add to Cart';
//                         this.style.backgroundColor = '';
//                     }, 1000);
                    
//                     // Show notification
//                     showNotification('Item added to cart!');
//                 });
//             });
            
//             // Function to show notification
//             function showNotification(message) {
//                 // Create notification element if it doesn't exist
//                 let notification = document.querySelector('.notification-popup');
                
//                 if (!notification) {
//                     notification = document.createElement('div');
//                     notification.className = 'notification-popup';
//                     notification.style.position = 'fixed';
//                     notification.style.bottom = '20px';
//                     notification.style.right = '20px';
//                     notification.style.background = 'rgba(52, 168, 83, 0.9)';
//                     notification.style.color = 'white';
//                     notification.style.padding = '12px 20px';
//                     notification.style.borderRadius = '8px';
//                     notification.style.boxShadow = '0 2px 10px rgba(0, 0, 0, 0.2)';
//                     notification.style.zIndex = '1000';
//                     notification.style.transition = 'all 0.3s ease';
//                     notification.style.opacity = '0';
//                     document.body.appendChild(notification);
//                 }
                
//                 // Update message and show
//                 notification.textContent = message;
//                 notification.style.opacity = '1';
                
//                 // Hide after 3 seconds
//                 setTimeout(() => {
//                     notification.style.opacity = '0';
//                     setTimeout(() => {
//                         notification.remove();
//                     }, 300);
//                 }, 3000);
//             }
            
//             // Function to update cart totals
//             function updateCartTotals() {
//                 // Recalculate cart totals based on current items and quantities
//                 let subtotal = 0;
                
//                 document.querySelectorAll('.cart-item').forEach(item => {
//                     const price = parseFloat(item.querySelector('.cart-item-price').textContent.replace(', '));
//                     const quantity = parseInt(item.querySelector('.quantity-value').textContent);
//                     subtotal += price * quantity;
//                 });
                
//                 // Update summary values
//                 const tax = subtotal * 0.08; // 8% tax
//                 const serviceFee = 0.50;
//                 const total = subtotal + tax + serviceFee;
                
//                 // Update display
//                 // const summaryLines = document.querySelectorAll('.summary-line');
//                 // if (summaryLines.length >= 4) {
//                 //     summaryLines[0].querySelectorAll('span')[1].textContent = ' + subtotal.toFixed(2);
//                 //     summaryLines[1].querySelectorAll('span')[1].textContent = ' + tax.toFixed(2);
//                 //     summaryLines[3].querySelectorAll('span')[1].textContent = ' + total.toFixed(2);
//                 // }
                
//                 // Update cart count in sidebar
//                 const cartItemCount = document.querySelectorAll('.cart-item').length;
//                 const cartMenu = document.querySelector('[data-page="cart"]');
//                 if (cartMenu) {
//                     cartMenu.innerHTML = `<i class="fas fa-shopping-cart"></i><span>Cart (${cartItemCount})</span>`;
//                 }
//             }
//         });