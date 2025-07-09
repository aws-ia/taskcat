// TaskCat Documentation Custom JavaScript

document.addEventListener('DOMContentLoaded', function() {
    // Add copy buttons to code blocks
    addCopyButtons();
    
    // Add smooth scrolling
    addSmoothScrolling();
    
    // Add table of contents highlighting
    addTocHighlighting();
    
    // Add parameter table enhancements
    enhanceParameterTables();
    
    // Add search enhancements
    enhanceSearch();
});

// Add copy buttons to code blocks
function addCopyButtons() {
    const codeBlocks = document.querySelectorAll('pre code');
    
    codeBlocks.forEach(function(codeBlock) {
        const pre = codeBlock.parentElement;
        const button = document.createElement('button');
        
        button.className = 'copy-button';
        button.innerHTML = '📋 Copy';
        button.setAttribute('aria-label', 'Copy code to clipboard');
        
        button.addEventListener('click', function() {
            navigator.clipboard.writeText(codeBlock.textContent).then(function() {
                button.innerHTML = '✅ Copied!';
                button.style.background = '#037f0c';
                
                setTimeout(function() {
                    button.innerHTML = '📋 Copy';
                    button.style.background = '';
                }, 2000);
            });
        });
        
        pre.style.position = 'relative';
        pre.appendChild(button);
    });
    
    // Add CSS for copy buttons
    const style = document.createElement('style');
    style.textContent = `
        .copy-button {
            position: absolute;
            top: 8px;
            right: 8px;
            background: #232f3e;
            color: white;
            border: none;
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 0.8em;
            cursor: pointer;
            opacity: 0;
            transition: opacity 0.2s ease;
        }
        
        pre:hover .copy-button {
            opacity: 1;
        }
        
        .copy-button:hover {
            background: #414d58;
        }
    `;
    document.head.appendChild(style);
}

// Add smooth scrolling for anchor links
function addSmoothScrolling() {
    const links = document.querySelectorAll('a[href^="#"]');
    
    links.forEach(function(link) {
        link.addEventListener('click', function(e) {
            const targetId = this.getAttribute('href').substring(1);
            const targetElement = document.getElementById(targetId);
            
            if (targetElement) {
                e.preventDefault();
                targetElement.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                });
            }
        });
    });
}

// Add table of contents highlighting
function addTocHighlighting() {
    const observer = new IntersectionObserver(function(entries) {
        entries.forEach(function(entry) {
            const id = entry.target.getAttribute('id');
            const tocLink = document.querySelector(`a[href="#${id}"]`);
            
            if (tocLink) {
                if (entry.isIntersecting) {
                    tocLink.classList.add('active');
                } else {
                    tocLink.classList.remove('active');
                }
            }
        });
    }, {
        rootMargin: '-20% 0px -80% 0px'
    });
    
    const headings = document.querySelectorAll('h1[id], h2[id], h3[id], h4[id], h5[id], h6[id]');
    headings.forEach(function(heading) {
        observer.observe(heading);
    });
}

// Enhance parameter tables with filtering and sorting
function enhanceParameterTables() {
    const tables = document.querySelectorAll('table');
    
    tables.forEach(function(table) {
        // Check if this is a parameter table
        const headers = table.querySelectorAll('th');
        const isParamTable = Array.from(headers).some(h => 
            h.textContent.toLowerCase().includes('parameter') ||
            h.textContent.toLowerCase().includes('pseudo')
        );
        
        if (isParamTable) {
            addTableFilter(table);
            addTableSorting(table);
        }
    });
}

// Add filter functionality to tables
function addTableFilter(table) {
    const wrapper = document.createElement('div');
    wrapper.className = 'table-wrapper';
    
    const filterInput = document.createElement('input');
    filterInput.type = 'text';
    filterInput.placeholder = '🔍 Filter parameters...';
    filterInput.className = 'table-filter';
    
    table.parentNode.insertBefore(wrapper, table);
    wrapper.appendChild(filterInput);
    wrapper.appendChild(table);
    
    filterInput.addEventListener('input', function() {
        const filterValue = this.value.toLowerCase();
        const rows = table.querySelectorAll('tbody tr');
        
        rows.forEach(function(row) {
            const text = row.textContent.toLowerCase();
            row.style.display = text.includes(filterValue) ? '' : 'none';
        });
    });
    
    // Add CSS for table filter
    const style = document.createElement('style');
    style.textContent = `
        .table-wrapper {
            margin: 1rem 0;
        }
        
        .table-filter {
            width: 100%;
            padding: 8px 12px;
            border: 1px solid #e9ebed;
            border-radius: 4px;
            margin-bottom: 1rem;
            font-size: 0.9em;
        }
        
        .table-filter:focus {
            outline: none;
            border-color: #0972d3;
            box-shadow: 0 0 0 2px rgba(9, 114, 211, 0.1);
        }
    `;
    document.head.appendChild(style);
}

// Add sorting functionality to tables
function addTableSorting(table) {
    const headers = table.querySelectorAll('th');
    
    headers.forEach(function(header, index) {
        header.style.cursor = 'pointer';
        header.style.userSelect = 'none';
        header.title = 'Click to sort';
        
        header.addEventListener('click', function() {
            sortTable(table, index);
        });
    });
}

// Sort table by column
function sortTable(table, columnIndex) {
    const tbody = table.querySelector('tbody');
    const rows = Array.from(tbody.querySelectorAll('tr'));
    
    const isAscending = table.getAttribute('data-sort-direction') !== 'asc';
    table.setAttribute('data-sort-direction', isAscending ? 'asc' : 'desc');
    
    rows.sort(function(a, b) {
        const aText = a.cells[columnIndex].textContent.trim();
        const bText = b.cells[columnIndex].textContent.trim();
        
        const comparison = aText.localeCompare(bText, undefined, { numeric: true });
        return isAscending ? comparison : -comparison;
    });
    
    rows.forEach(function(row) {
        tbody.appendChild(row);
    });
    
    // Update header indicators
    const headers = table.querySelectorAll('th');
    headers.forEach(function(h) {
        h.classList.remove('sort-asc', 'sort-desc');
    });
    headers[columnIndex].classList.add(isAscending ? 'sort-asc' : 'sort-desc');
}

// Enhance search functionality
function enhanceSearch() {
    const searchInput = document.querySelector('.md-search__input');
    
    if (searchInput) {
        // Add search suggestions
        searchInput.addEventListener('input', function() {
            const query = this.value.toLowerCase();
            
            if (query.length > 2) {
                highlightSearchTerms(query);
            }
        });
    }
}

// Highlight search terms in content
function highlightSearchTerms(query) {
    const content = document.querySelector('.md-content');
    const walker = document.createTreeWalker(
        content,
        NodeFilter.SHOW_TEXT,
        null,
        false
    );
    
    const textNodes = [];
    let node;
    
    while (node = walker.nextNode()) {
        textNodes.push(node);
    }
    
    textNodes.forEach(function(textNode) {
        const parent = textNode.parentNode;
        if (parent.tagName !== 'SCRIPT' && parent.tagName !== 'STYLE') {
            const text = textNode.textContent;
            const regex = new RegExp(`(${query})`, 'gi');
            
            if (regex.test(text)) {
                const highlightedText = text.replace(regex, '<mark>$1</mark>');
                const span = document.createElement('span');
                span.innerHTML = highlightedText;
                parent.replaceChild(span, textNode);
            }
        }
    });
}

// Add keyboard shortcuts
document.addEventListener('keydown', function(e) {
    // Ctrl/Cmd + K to focus search
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

// Add progress indicator for long pages
function addProgressIndicator() {
    const progressBar = document.createElement('div');
    progressBar.className = 'progress-bar';
    progressBar.innerHTML = '<div class="progress-fill"></div>';
    
    document.body.appendChild(progressBar);
    
    window.addEventListener('scroll', function() {
        const scrollTop = window.pageYOffset;
        const docHeight = document.body.scrollHeight - window.innerHeight;
        const scrollPercent = (scrollTop / docHeight) * 100;
        
        const progressFill = document.querySelector('.progress-fill');
        progressFill.style.width = scrollPercent + '%';
    });
    
    // Add CSS for progress bar
    const style = document.createElement('style');
    style.textContent = `
        .progress-bar {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 3px;
            background: rgba(255, 255, 255, 0.1);
            z-index: 1000;
        }
        
        .progress-fill {
            height: 100%;
            background: #ff9900;
            transition: width 0.1s ease;
        }
    `;
    document.head.appendChild(style);
}

// Initialize progress indicator
addProgressIndicator();
