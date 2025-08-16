// Cyborg Theme Enhancements for taskcat Documentation

document.addEventListener('DOMContentLoaded', function() {
    // Initialize Cyborg theme enhancements
    initCyborgTheme();
    addCodeCopyButtons();
    enhanceNavigation();
    addKeyboardShortcuts();
    addNeonEffects();
});

// Initialize Cyborg theme
function initCyborgTheme() {
    // Add theme class to body
    document.body.classList.add('cyborg-theme');
    
    // Add theme version to footer
    const footer = document.querySelector('.md-footer-copyright');
    if (footer) {
        const themeInfo = document.createElement('div');
        themeInfo.className = 'md-footer-theme-info';
        themeInfo.innerHTML = 'Powered by <a href="https://bootswatch.com/cyborg/">Cyborg</a>';
        footer.appendChild(themeInfo);
    }
}

// Add copy buttons to code blocks
function addCodeCopyButtons() {
    const codeBlocks = document.querySelectorAll('.highlight pre');
    
    codeBlocks.forEach(function(codeBlock) {
        const wrapper = document.createElement('div');
        wrapper.className = 'code-wrapper';
        wrapper.style.position = 'relative';
        
        codeBlock.parentNode.insertBefore(wrapper, codeBlock);
        wrapper.appendChild(codeBlock);
        
        const copyButton = document.createElement('button');
        copyButton.className = 'copy-button';
        copyButton.innerHTML = '<span class="copy-icon">⚡</span> Copy';
        copyButton.setAttribute('aria-label', 'Copy code to clipboard');
        copyButton.style.cssText = `
            position: absolute;
            top: 5px;
            right: 5px;
            background: #2a9fd6;
            color: #fff;
            border: none;
            border-radius: 3px;
            padding: 5px 10px;
            font-size: 12px;
            cursor: pointer;
            opacity: 0.8;
            transition: all 0.3s ease;
            z-index: 10;
        `;
        
        copyButton.addEventListener('mouseenter', function() {
            this.style.opacity = '1';
            this.style.boxShadow = '0 0 10px rgba(42, 159, 214, 0.7)';
        });
        
        copyButton.addEventListener('mouseleave', function() {
            this.style.opacity = '0.8';
            this.style.boxShadow = 'none';
        });
        
        copyButton.addEventListener('click', function() {
            const code = codeBlock.textContent;
            
            if (navigator.clipboard && window.isSecureContext) {
                navigator.clipboard.writeText(code).then(function() {
                    showCopySuccess(copyButton);
                }).catch(function() {
                    fallbackCopy(code, copyButton);
                });
            } else {
                fallbackCopy(code, copyButton);
            }
        });
        
        wrapper.appendChild(copyButton);
    });
}

// Fallback copy method for older browsers
function fallbackCopy(text, button) {
    const textArea = document.createElement('textarea');
    textArea.value = text;
    textArea.style.position = 'fixed';
    textArea.style.left = '-999999px';
    textArea.style.top = '-999999px';
    document.body.appendChild(textArea);
    textArea.focus();
    textArea.select();
    
    try {
        document.execCommand('copy');
        showCopySuccess(button);
    } catch (err) {
        console.error('Failed to copy text: ', err);
        button.innerHTML = '<span class="copy-icon">❌</span> Failed';
        button.style.background = '#cc0000';
        setTimeout(function() {
            button.innerHTML = '<span class="copy-icon">⚡</span> Copy';
            button.style.background = '#2a9fd6';
        }, 2000);
    }
    
    document.body.removeChild(textArea);
}

// Show copy success feedback
function showCopySuccess(button) {
    const originalText = button.innerHTML;
    button.innerHTML = '<span class="copy-icon">✓</span> Copied!';
    button.style.background = '#77b300';
    button.style.boxShadow = '0 0 10px rgba(119, 179, 0, 0.7)';
    
    setTimeout(function() {
        button.innerHTML = originalText;
        button.style.background = '#2a9fd6';
        button.style.boxShadow = '0 0 10px rgba(42, 159, 214, 0.7)';
    }, 2000);
}

// Enhance navigation
function enhanceNavigation() {
    // Add active class to current page in navigation
    const currentPath = window.location.pathname;
    const navLinks = document.querySelectorAll('.md-nav__link');
    
    navLinks.forEach(function(link) {
        const href = link.getAttribute('href');
        if (href && currentPath.endsWith(href)) {
            link.classList.add('md-nav__link--active');
            link.style.borderLeft = '3px solid #2a9fd6';
            link.style.paddingLeft = '10px';
            
            // Expand parent sections
            let parent = link.parentElement;
            while (parent) {
                if (parent.classList.contains('md-nav__item--nested')) {
                    parent.classList.add('md-nav__item--expanded');
                    const input = parent.querySelector('input');
                    if (input) {
                        input.checked = true;
                    }
                }
                parent = parent.parentElement;
            }
        }
    });
    
    // Add hover effects to navigation links
    navLinks.forEach(function(link) {
        link.addEventListener('mouseenter', function() {
            if (!this.classList.contains('md-nav__link--active')) {
                this.style.borderLeft = '3px solid #9933cc';
                this.style.paddingLeft = '10px';
                this.style.transition = 'all 0.3s ease';
            }
        });
        
        link.addEventListener('mouseleave', function() {
            if (!this.classList.contains('md-nav__link--active')) {
                this.style.borderLeft = 'none';
                this.style.paddingLeft = '0';
            }
        });
    });
}

// Add keyboard shortcuts
function addKeyboardShortcuts() {
    document.addEventListener('keydown', function(e) {
        // Ctrl/Cmd + K for search
        if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
            e.preventDefault();
            const searchInput = document.querySelector('.md-search__input');
            if (searchInput) {
                searchInput.focus();
            }
        }
        
        // Escape to close search
        if (e.key === 'Escape') {
            const searchInput = document.querySelector('.md-search__input');
            if (searchInput && document.activeElement === searchInput) {
                searchInput.blur();
            }
        }
    });
}

// Add neon effects for Cyborg theme
function addNeonEffects() {
    // Add neon effect to headings
    const headings = document.querySelectorAll('h1, h2, h3');
    headings.forEach(function(heading) {
        heading.addEventListener('mouseenter', function() {
            this.style.textShadow = '0 0 10px currentColor';
            this.style.transition = 'text-shadow 0.3s ease';
        });
        
        heading.addEventListener('mouseleave', function() {
            this.style.textShadow = 'none';
        });
    });
    
    // Add neon effect to code blocks
    const codeBlocks = document.querySelectorAll('.highlight');
    codeBlocks.forEach(function(block) {
        block.addEventListener('mouseenter', function() {
            this.style.boxShadow = '0 0 15px rgba(42, 159, 214, 0.5)';
            this.style.transition = 'box-shadow 0.3s ease';
        });
        
        block.addEventListener('mouseleave', function() {
            this.style.boxShadow = 'none';
        });
    });
    
    // Add neon effect to buttons
    const buttons = document.querySelectorAll('.md-button');
    buttons.forEach(function(button) {
        button.addEventListener('mouseenter', function() {
            this.style.boxShadow = '0 0 15px rgba(42, 159, 214, 0.7)';
            this.style.transition = 'all 0.3s ease';
        });
        
        button.addEventListener('mouseleave', function() {
            this.style.boxShadow = 'none';
        });
    });
}

// Add smooth scrolling for anchor links
function addSmoothScrolling() {
    document.querySelectorAll('a[href^="#"]').forEach(function(anchor) {
        anchor.addEventListener('click', function(e) {
            const targetId = this.getAttribute('href').substring(1);
            const targetElement = document.getElementById(targetId);
            
            if (targetElement) {
                e.preventDefault();
                targetElement.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                });
                
                // Update URL without jumping
                history.pushState(null, null, '#' + targetId);
            }
        });
    });
}

// Initialize smooth scrolling
setTimeout(addSmoothScrolling, 1000);

// Add accessibility features
function addAccessibilityFeatures() {
    // Add skip to content link
    const skipLink = document.createElement('a');
    skipLink.href = '#main-content';
    skipLink.textContent = 'Skip to main content';
    skipLink.className = 'skip-link';
    skipLink.style.cssText = `
        position: absolute;
        top: -40px;
        left: 0;
        background: #2a9fd6;
        color: #fff;
        padding: 8px;
        z-index: 1000;
        transition: top 0.3s;
    `;
    
    skipLink.addEventListener('focus', function() {
        this.style.top = '0';
    });
    
    skipLink.addEventListener('blur', function() {
        this.style.top = '-40px';
    });
    
    document.body.insertBefore(skipLink, document.body.firstChild);
    
    // Add main content landmark
    const content = document.querySelector('.md-content');
    if (content) {
        content.setAttribute('id', 'main-content');
        content.setAttribute('role', 'main');
    }
}

// Initialize accessibility features
setTimeout(addAccessibilityFeatures, 500);

// Add print styles
function addPrintStyles() {
    const printStyles = document.createElement('style');
    printStyles.textContent = `
        @media print {
            .md-header, .md-tabs, .md-sidebar, .md-footer, .md-top, .md-dialog, .md-search {
                display: none !important;
            }
            
            .md-content {
                margin: 0 !important;
                max-width: 100% !important;
            }
            
            .md-content__inner {
                padding: 0 !important;
                margin: 0 !important;
            }
            
            body {
                color: black !important;
                background: white !important;
            }
            
            h1, h2, h3, h4, h5, h6 {
                color: black !important;
                break-after: avoid !important;
            }
            
            pre, blockquote, tr, img {
                break-inside: avoid !important;
            }
            
            .copy-button {
                display: none !important;
            }
        }
    `;
    document.head.appendChild(printStyles);
}

// Initialize print styles
addPrintStyles();
