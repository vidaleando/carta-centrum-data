import Root from './Root.svelte';

const app = new Root({
  target: document.getElementById('app')
});

// Register Service Worker for PWA
if ('serviceWorker' in navigator && import.meta.env.PROD) {
  navigator.serviceWorker.register('/sw.js')
    .then(reg => console.log('SW registered:', reg.scope))
    .catch(err => console.log('SW registration failed:', err));
} else if ('serviceWorker' in navigator) {
  // Dev: drop any worker left over from a production build on this origin.
  navigator.serviceWorker.getRegistrations()
    .then(regs => regs.forEach(reg => reg.unregister()));
}

export default app;
