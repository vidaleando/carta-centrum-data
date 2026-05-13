import App from './App.svelte';

const app = new App({
  target: document.getElementById('app')
});

// Register Service Worker for PWA
if ('serviceWorker' in navigator && import.meta.env.PROD) {
  navigator.serviceWorker.register('/sw.js')
    .then(reg => console.log('SW registered:', reg.scope))
    .catch(err => console.log('SW registration failed:', err));
}

export default app;
