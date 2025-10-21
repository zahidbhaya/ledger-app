// === MULTI-THEME CYCLER ===
const htmlEl = document.documentElement;
const toggleBtn = document.getElementById('theme-toggle');

// All available themes (add more easily)
const themes = ['violet', 'light', 'emerald', 'royal', 'sunset', 'aqua', 'rose'];

let savedTheme = localStorage.getItem('theme') || 'violet';
if (!themes.includes(savedTheme)) savedTheme = 'violet';
htmlEl.setAttribute('data-theme', savedTheme);

// show emoji hint
const emojis = {
    violet: '🌌', light: '🌤️', emerald: '🌿', royal: '💙', sunset: '🌇', aqua: '🌊', rose: '🌸'
};
toggleBtn.textContent = `${emojis[savedTheme]} Theme`;

if (toggleBtn) {
    toggleBtn.addEventListener('click', () => {
        const current = htmlEl.getAttribute('data-theme');
        const next = themes[(themes.indexOf(current) + 1) % themes.length];
        htmlEl.setAttribute('data-theme', next);
        localStorage.setItem('theme', next);
        toggleBtn.textContent = `${emojis[next]} Theme`;
    });
}
// === BLINK EFFECT FOR WELCOME BANNER ===
document.addEventListener('DOMContentLoaded', () => {
    const banner = document.getElementById('welcome-banner');
    if (!banner) return;

    let glow = false;
    setInterval(() => {
        glow = !glow;
        banner.classList.toggle('blink', glow);
    }, 1200); // blink every 1.2 seconds
});
