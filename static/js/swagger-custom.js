document.addEventListener('DOMContentLoaded', function() {
    // Add favicon
    const favicon = document.createElement('link');
    favicon.rel = 'icon';
    favicon.href = '/static/favicon.ico';
    document.head.appendChild(favicon);

    // Optional: Add dark mode toggle
    const toggle = document.createElement('button');
    toggle.innerText = 'Toggle Dark Mode';
    toggle.style.position = 'fixed';
    toggle.style.top = '10px';
    toggle.style.right = '10px';
    toggle.onclick = () => document.body.classList.toggle('dark-mode');
    document.body.prepend(toggle);
});

// Dark mode styles (loaded dynamically)
const style = document.createElement('style');
style.innerHTML = `
    .dark-mode {
        background-color: #333;
        color: #fff;
    }
    .dark-mode .swagger-ui .opblock {
        background-color: #444;
    }
    .dark-mode .swagger-ui .info {
        background: linear-gradient(to right, #1b5e20, #4caf50);
    }
`;
document.head.appendChild(style);