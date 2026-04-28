import type { PlayPushSubscriptionPayload } from '../types';

function urlBase64ToUint8Array(base64String: string) {
  const normalized = base64String.replace(/-/g, '+').replace(/_/g, '/');
  const padding = '='.repeat((4 - (normalized.length % 4)) % 4);
  const rawData = window.atob(`${normalized}${padding}`);
  return Uint8Array.from(rawData, (character) => character.charCodeAt(0));
}

export function isPlayPushSupported() {
  return typeof window !== 'undefined' && 'serviceWorker' in navigator && 'PushManager' in window;
}

async function ensureNotificationPermission() {
  if (typeof Notification === 'undefined') {
    return 'unsupported';
  }
  if (Notification.permission === 'granted') {
    return 'granted';
  }
  return Notification.requestPermission();
}

async function ensureServiceWorkerRegistration(serviceWorkerPath: string) {
  const existing = await navigator.serviceWorker.getRegistration();
  if (existing?.active) {
    return existing;
  }
  if (!existing) {
    await navigator.serviceWorker.register(serviceWorkerPath);
  }
  return navigator.serviceWorker.ready;
}

export async function subscribeBrowserToPlayPush(publicVapidKey: string, serviceWorkerPath: string): Promise<PlayPushSubscriptionPayload> {
  if (!isPlayPushSupported()) {
    throw new Error('Questo browser non supporta le web push.');
  }
  const permission = await ensureNotificationPermission();
  if (permission !== 'granted') {
    throw new Error('Permesso notifiche non concesso.');
  }

  const registration = await ensureServiceWorkerRegistration(serviceWorkerPath);
  const existingSubscription = await registration.pushManager.getSubscription();
  let subscription = existingSubscription;
  if (!subscription) {
    try {
      subscription = await registration.pushManager.subscribe({
        userVisibleOnly: true,
        applicationServerKey: urlBase64ToUint8Array(publicVapidKey),
      });
    } catch (error) {
      const message = error instanceof Error ? error.message : '';
      if (/permission denied/i.test(message)) {
        throw new Error('Questo browser non consente la registrazione web push in questo contesto. Se stai usando il browser integrato o una finestra privata, apri la pagina in Chrome o Edge normale.');
      }
      throw error;
    }
  }
  const serialized = subscription.toJSON();

  if (!serialized.endpoint || !serialized.keys?.p256dh || !serialized.keys?.auth) {
    throw new Error('Il browser ha restituito una subscription push incompleta.');
  }

  return {
    endpoint: serialized.endpoint,
    keys: {
      p256dh: serialized.keys.p256dh,
      auth: serialized.keys.auth,
    },
    user_agent: navigator.userAgent,
  };
}


export async function getBrowserPlayPushEndpoint() {
  if (!isPlayPushSupported()) {
    return null;
  }

  const registration = await navigator.serviceWorker.getRegistration();
  if (!registration) {
    return null;
  }

  const subscription = await registration.pushManager.getSubscription();
  return subscription?.endpoint || null;
}


export async function unsubscribeBrowserFromPlayPush() {
  if (!isPlayPushSupported()) {
    return null;
  }
  const registration = await navigator.serviceWorker.getRegistration();
  if (!registration) {
    return null;
  }
  const subscription = await registration.pushManager.getSubscription();
  if (!subscription) {
    return null;
  }
  const endpoint = subscription.endpoint;
  await subscription.unsubscribe();
  return endpoint;
}