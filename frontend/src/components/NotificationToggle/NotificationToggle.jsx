import { useState, useEffect } from 'react'
import { api } from '../../api/client.js'
import './NotificationToggle.css'

function urlBase64ToUint8Array(base64String) {
  const padding = '='.repeat((4 - (base64String.length % 4)) % 4)
  const base64 = (base64String + padding)
    .replace(/-/g, '+')
    .replace(/_/g, '/')

  const rawData = window.atob(base64)
  const outputArray = new Uint8Array(rawData.length)

  for (let i = 0; i < rawData.length; ++i) {
    outputArray[i] = rawData.charCodeAt(i)
  }
  return outputArray
}

export default function NotificationToggle({ onSubscriptionChange }) {
  const [isSupported, setIsSupported] = useState(false)
  const [isSubscribed, setIsSubscribed] = useState(false)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const supported =
      'serviceWorker' in navigator &&
      'PushManager' in window &&
      'Notification' in window
    setIsSupported(supported)

    if (supported) {
      checkSubscription()
    } else {
      setLoading(false)
      if (onSubscriptionChange) {
        onSubscriptionChange(false)
      }
    }
  }, [])

  const checkSubscription = async () => {
    try {
      const registration = await navigator.serviceWorker.ready
      const subscription = await registration.pushManager.getSubscription()
      const subscribed = !!subscription
      setIsSubscribed(subscribed)
      if (onSubscriptionChange) {
        onSubscriptionChange(subscribed)
      }
    } catch (err) {
      console.error('Error checking push subscription:', err)
    } finally {
      setLoading(false)
    }
  }

  const handleToggle = async () => {
    if (!isSupported || loading) return

    setLoading(true)
    try {
      if (isSubscribed) {
        const registration = await navigator.serviceWorker.ready
        const subscription = await registration.pushManager.getSubscription()
        if (subscription) {
          await subscription.unsubscribe()
        }
        setIsSubscribed(false)
        if (onSubscriptionChange) {
          onSubscriptionChange(false)
        }
      } else {
        const perm = await Notification.requestPermission()
        if (perm !== 'granted') {
          alert('Notification permission denied. Please enable notifications in your browser settings.')
          setLoading(false)
          return
        }

        const { publicKey: vapidPublicKey } = await api.getVapidPublicKey()
        const registration = await navigator.serviceWorker.ready
        const subscription = await registration.pushManager.subscribe({
          userVisibleOnly: true,
          applicationServerKey: urlBase64ToUint8Array(vapidPublicKey)
        })

        await api.subscribeNotifications(subscription.toJSON())
        setIsSubscribed(true)
        if (onSubscriptionChange) {
          onSubscriptionChange(true)
        }
      }
    } catch (err) {
      console.error('Failed to toggle subscription:', err)
      alert('Failed to update subscription. Please ensure you are running over a secure connection (localhost or HTTPS).')
    } finally {
      setLoading(false)
    }
  }

  if (!isSupported) return null

  return (
    <button
      onClick={handleToggle}
      disabled={loading}
      className={`notification-toggle-btn ${isSubscribed ? 'notification-toggle-btn--active' : ''}`}
      title={isSubscribed ? 'Disable live score notifications' : 'Enable live score notifications'}
      aria-label="Toggle notifications"
      id="notification-toggle-button"
    >
      {loading ? (
        <span className="spinner-small" />
      ) : isSubscribed ? (
        <svg viewBox="0 0 24 24" width="20" height="20" fill="currentColor" stroke="currentColor" strokeWidth="0">
          <path d="M12 22c1.1 0 2-.9 2-2h-4c0 1.1.89 2 2 2zm6-6v-5c0-3.07-1.64-5.64-4.5-6.32V4c0-.83-.67-1.5-1.5-1.5s-1.5.67-1.5 1.5v.68C7.63 5.36 6 7.92 6 11v5l-2 2v1h16v-1l-2-2z"/>
        </svg>
      ) : (
        <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9" />
          <path d="M13.73 21a2 2 0 0 1-3.46 0" />
        </svg>
      )}
    </button>
  )
}
