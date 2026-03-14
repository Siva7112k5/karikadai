// main.js - All JavaScript functionality for Frozen Kadai

$(document).ready(function() {
    // ============================================
    // LOCATION PICKER
    // ============================================
    $('#setLocation').click(function() {
        var location = $('#locationPicker').val();
        if (location) {
            $.ajax({
                url: '/set-location',
                type: 'POST',
                contentType: 'application/json',
                data: JSON.stringify({location: location}),
                success: function(response) {
                    if (response.success) {
                        showNotification('Delivery location set to: ' + location, 'success');
                        $('#locationPicker').val(location);
                    }
                },
                error: function() {
                    showNotification('Error setting location. Please try again.', 'error');
                }
            });
        } else {
            showNotification('Please enter a delivery location', 'warning');
        }
    });

    // ============================================
    // ADD TO CART FUNCTIONALITY
    // ============================================
    $('.add-to-cart').click(function() {
        var productId = $(this).data('product-id');
        var button = $(this);
        
        {% if current_user.is_authenticated %}
            button.prop('disabled', true).html('<i class="fas fa-spinner fa-spin"></i> Adding...');
            
            $.ajax({
                url: '/add-to-cart',
                type: 'POST',
                data: {
                    product_id: productId,
                    quantity: 1.0
                },
                success: function(response) {
                    showNotification('Product added to cart!', 'success');
                    updateCartCount();
                },
                error: function(xhr) {
                    if (xhr.status === 401) {
                        window.location.href = '/login';
                    } else {
                        showNotification('Error adding to cart. Please try again.', 'error');
                    }
                },
                complete: function() {
                    button.prop('disabled', false).html('Add to Cart');
                }
            });
        {% else %}
            window.location.href = '/login?next=' + window.location.pathname;
        {% endif %}
    });

    // ============================================
    // QUANTITY INPUT VALIDATION
    // ============================================
    $('.quantity-input').on('input', function() {
        var value = parseFloat($(this).val());
        var min = parseFloat($(this).attr('min')) || 0.5;
        var step = parseFloat($(this).attr('step')) || 0.5;
        
        // Round to nearest step
        value = Math.round(value / step) * step;
        
        // Ensure minimum
        if (value < min) {
            value = min;
        }
        
        $(this).val(value.toFixed(1));
    });

    // ============================================
    // FLASH SALE TIMER
    // ============================================
    function initializeTimers() {
        $('.flash-timer').each(function() {
            var endTime = new Date();
            endTime.setHours(endTime.getHours() + 24); // 24 hour sale
            
            var timer = setInterval(function() {
                var now = new Date().getTime();
                var distance = endTime - now;
                
                var hours = Math.floor(distance / (1000 * 60 * 60));
                var minutes = Math.floor((distance % (1000 * 60 * 60)) / (1000 * 60));
                var seconds = Math.floor((distance % (1000 * 60)) / 1000);
                
                $('#hours').text(('0' + hours).slice(-2));
                $('#minutes').text(('0' + minutes).slice(-2));
                $('#seconds').text(('0' + seconds).slice(-2));
                
                if (distance < 0) {
                    clearInterval(timer);
                    $('#hours, #minutes, #seconds').text('00');
                }
            }, 1000);
        });
    }

    // ============================================
    // SEARCH AUTOCOMPLETE (Optional Enhancement)
    // ============================================
    var searchTimeout;
    $('input[name="search"]').on('input', function() {
        clearTimeout(searchTimeout);
        var query = $(this).val();
        
        if (query.length < 2) return;
        
        searchTimeout = setTimeout(function() {
            $.ajax({
                url: '/api/search-suggestions',
                type: 'GET',
                data: {q: query},
                success: function(suggestions) {
                    // Display suggestions dropdown
                    showSearchSuggestions(suggestions);
                }
            });
        }, 300);
    });

    function showSearchSuggestions(suggestions) {
        // Implementation for search suggestions dropdown
        // This can be enhanced based on your needs
    }

    // ============================================
    // PRODUCT QUICK VIEW MODAL
    // ============================================
    $('.quick-view-btn').click(function() {
        var productId = $(this).data('product-id');
        
        $.ajax({
            url: '/api/product/' + productId,
            type: 'GET',
            success: function(product) {
                showQuickViewModal(product);
            }
        });
    });

    function showQuickViewModal(product) {
        // Create and show modal with product details
        var modal = `
            <div class="modal fade" id="quickViewModal" tabindex="-1">
                <div class="modal-dialog modal-lg">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title">${product.name}</h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                        </div>
                        <div class="modal-body">
                            <div class="row">
                                <div class="col-md-6">
                                    <img src="/static/images/${product.image_file}" class="img-fluid">
                                </div>
                                <div class="col-md-6">
                                    <h4 class="text-danger">₹${product.price_per_kg}/kg</h4>
                                    <p>${product.description}</p>
                                    <button class="btn btn-danger add-to-cart" data-product-id="${product.id}">
                                        Add to Cart
                                    </button>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        $('body').append(modal);
        $('#quickViewModal').modal('show');
        $('#quickViewModal').on('hidden.bs.modal', function() {
            $(this).remove();
        });
    }

    // ============================================
    // CART MANAGEMENT
    // ============================================
    function updateCartCount() {
        $.ajax({
            url: '/api/cart-count',
            type: 'GET',
            success: function(response) {
                $('.cart-count').text(response.count);
            }
        });
    }

    // ============================================
    // NOTIFICATION SYSTEM
    // ============================================
    function showNotification(message, type) {
        // Create notification element
        var notification = `
            <div class="alert alert-${type} alert-dismissible fade show notification-toast" role="alert">
                ${message}
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            </div>
        `;
        
        // Add to page
        var container = $('.notification-container');
        if (container.length === 0) {
            container = $('<div class="notification-container position-fixed top-0 end-0 p-3" style="z-index: 9999;"></div>');
            $('body').append(container);
        }
        
        container.append(notification);
        
        // Auto remove after 3 seconds
        setTimeout(function() {
            notification.fadeOut('slow', function() {
                $(this).remove();
            });
        }, 3000);
    }

    // ============================================
    // PRICE CALCULATOR (for product page)
    // ============================================
    $('#quantity').on('input', function() {
        var quantity = parseFloat($(this).val()) || 0.5;
        var pricePerKg = parseFloat($('#price-per-kg').data('price'));
        var total = quantity * pricePerKg;
        
        $('#total-price').text('₹' + total.toFixed(2));
    });

    // ============================================
    // SUBSCRIPTION TOGGLE
    // ============================================
    $('#subscriptionCheck').change(function() {
        if ($(this).is(':checked')) {
            $('.price-display').addClass('text-success');
            // Apply 10% discount logic
            var originalPrice = parseFloat($('#total-price').data('original'));
            var discountedPrice = originalPrice * 0.9;
            $('#total-price').text('₹' + discountedPrice.toFixed(2));
        } else {
            $('.price-display').removeClass('text-success');
            var originalPrice = parseFloat($('#total-price').data('original'));
            $('#total-price').text('₹' + originalPrice.toFixed(2));
        }
    });

    // ============================================
    // THAWING INSTRUCTIONS TOGGLE
    // ============================================
    $('#thawingToggle').click(function() {
        $('#thawingInstructions').slideToggle();
    });

    // ============================================
    // PRODUCT FILTERING
    // ============================================
    $('#categoryFilter').change(function() {
        var category = $(this).val();
        filterProducts(category);
    });

    function filterProducts(category) {
        window.location.href = '/products?category=' + category;
    }

    // ============================================
    // PRICE RANGE FILTER
    // ============================================
    $('#priceRange').on('input', function() {
        var value = $(this).val();
        $('#priceValue').text('₹' + value);
    });

    // ============================================
    // WISHLIST FUNCTIONALITY
    // ============================================
    $('.add-to-wishlist').click(function() {
        var productId = $(this).data('product-id');
        var button = $(this);
        
        $.ajax({
            url: '/api/wishlist/add',
            type: 'POST',
            data: {product_id: productId},
            success: function() {
                button.toggleClass('far fas');
                showNotification('Added to wishlist!', 'success');
            }
        });
    });

    // ============================================
    // REVIEW SYSTEM
    // ============================================
    $('.rating-input i').hover(
        function() {
            var rating = $(this).data('rating');
            highlightStars(rating);
        },
        function() {
            resetStars();
        }
    );

    $('.rating-input i').click(function() {
        var rating = $(this).data('rating');
        $('#rating-value').val(rating);
        setStars(rating);
    });

    function highlightStars(rating) {
        $('.rating-input i').each(function(index) {
            if (index < rating) {
                $(this).addClass('fas').removeClass('far');
            } else {
                $(this).addClass('far').removeClass('fas');
            }
        });
    }

    function resetStars() {
        var currentRating = $('#rating-value').val();
        setStars(currentRating);
    }

    function setStars(rating) {
        $('.rating-input i').each(function(index) {
            if (index < rating) {
                $(this).addClass('fas').removeClass('far');
            } else {
                $(this).addClass('far').removeClass('fas');
            }
        });
    }

    // ============================================
    // LAZY LOAD IMAGES
    // ============================================
    if ('IntersectionObserver' in window) {
        const imageObserver = new IntersectionObserver((entries, observer) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    const image = entry.target;
                    image.src = image.dataset.src;
                    image.classList.remove('lazy');
                    imageObserver.unobserve(image);
                }
            });
        });

        const images = document.querySelectorAll('img.lazy');
        images.forEach(img => imageObserver.observe(img));
    }

    // ============================================
    // BACK TO TOP BUTTON
    // ============================================
    var backToTop = $('<button>', {
        'class': 'btn btn-danger back-to-top',
        'html': '<i class="fas fa-arrow-up"></i>',
        'click': function() {
            $('html, body').animate({scrollTop: 0}, 500);
        }
    }).css({
        'position': 'fixed',
        'bottom': '20px',
        'right': '20px',
        'display': 'none',
        'z-index': '99',
        'border-radius': '50%',
        'width': '50px',
        'height': '50px'
    });

    $('body').append(backToTop);

    $(window).scroll(function() {
        if ($(this).scrollTop() > 300) {
            $('.back-to-top').fadeIn();
        } else {
            $('.back-to-top').fadeOut();
        }
    });

    // ============================================
    // INITIALIZATION
    // ============================================
    initializeTimers();
    
    // Bootstrap tooltips
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function(tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // Bootstrap popovers
    var popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    popoverTriggerList.map(function(popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });
});

// ============================================
// EXPORT FUNCTIONS FOR GLOBAL USE
// ============================================
window.FrozenKadai = {
    showNotification: showNotification,
    updateCartCount: updateCartCount,
    filterProducts: filterProducts
};