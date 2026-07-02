import { useState, useEffect, useRef } from 'react'
import { createPortal } from 'react-dom'
import { api } from '../../api/client.js'
import './PageSubscribeButton.css'

export default function PageSubscribeButton({ topicType, topicId, topicName }) {
  const [isSupported, setIsSupported] = useState(false)
  const [isSubscribed, setIsSubscribed] = useState(false)
  const [showPopup, setShowPopup] = useState(false)
  const [loading, setLoading] = useState(true)
  
  const [notifyOutcome, setNotifyOutcome] = useState(true)
  const [notifyEvents, setNotifyEvents] = useState(false)
  
  const buttonRef = useRef(null)
  const popupRef = useRef(null)
  const [isMobile, setIsMobile] = useState(window.innerWidth <= 768)

  useEffect(() => {
    const handleResize = () => {
      setIsMobile(window.innerWidth <= 768)
    }
    window.addEventListener('resize', handleResize)
    return () => window.removeEventListener('resize', handleResize)
  }, [])

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
    }
  }, [topicId, topicType])

  // Close popup when clicking outside
  useEffect(() => {
    function handleClickOutside(event) {
      const clickedButton = buttonRef.current && buttonRef.current.contains(event.target)
      const clickedPopup = popupRef.current && popupRef.current.contains(event.target)
      if (!clickedButton && !clickedPopup) {
        setShowPopup(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  const checkSubscription = async () => {
    try {
      const registration = await navigator.serviceWorker.ready
      const subscription = await registration.pushManager.getSubscription()
      if (subscription) {
        const res = await api.getMySubscriptions(subscription.endpoint)
        const active = (res.subscriptions || []).find(
          item => item.topic_type === topicType && item.topic_id === parseInt(topicId)
        )
        if (active) {
          setIsSubscribed(true)
          setNotifyOutcome(active.notify_outcome)
          setNotifyEvents(active.notify_events)
        } else {
          setIsSubscribed(false)
          setNotifyOutcome(true)
          setNotifyEvents(false)
        }
      }
    } catch (err) {
      console.error('Error checking topic subscription:', err)
    } finally {
      setLoading(false)
    }
  }

  const handleToggleClick = async () => {
    if (loading) return

    // 1. Check if notifications are enabled globally
    const registration = await navigator.serviceWorker.ready
    const subscription = await registration.pushManager.getSubscription()
    if (!subscription || Notification.permission !== 'granted') {
      alert('Push notifications are not active on this device. Please open the Notifications tab and allow alerts first!')
      return
    }

    setShowPopup(!showPopup)
  }

  const handleSaveSubscription = async () => {
    setLoading(true)
    setShowPopup(false)
    try {
      const registration = await navigator.serviceWorker.ready
      const subscription = await registration.pushManager.getSubscription()
      if (!subscription) return

      await api.toggleSubscriptionTopic({
        endpoint: subscription.endpoint,
        topic_type: topicType,
        topic_id: parseInt(topicId),
        subscribe: true,
        notify_outcome: notifyOutcome,
        notify_events: notifyEvents
      })

      setIsSubscribed(true)
    } catch (err) {
      console.error('Error saving subscription topic:', err)
      alert('Failed to update subscription.')
    } finally {
      setLoading(false)
    }
  }

  const handleUnsubscribe = async () => {
    setLoading(true)
    setShowPopup(false)
    try {
      const registration = await navigator.serviceWorker.ready
      const subscription = await registration.pushManager.getSubscription()
      if (!subscription) return

      await api.toggleSubscriptionTopic({
        endpoint: subscription.endpoint,
        topic_type: topicType,
        topic_id: parseInt(topicId),
        subscribe: false
      })

      setIsSubscribed(false)
      setNotifyOutcome(true)
      setNotifyEvents(false)
    } catch (err) {
      console.error('Error removing subscription topic:', err)
      alert('Failed to unsubscribe.')
    } finally {
      setLoading(false)
    }
  }

  if (!isSupported) return null

  const popupContent = (
    <div className="page-subscribe-popup" ref={popupRef}>
      <div className="page-subscribe-popup__title">
        Alerts: {topicName}
      </div>
      
      <label className="page-subscribe-popup__option">
        <input 
          type="checkbox" 
          checked={notifyOutcome}
          onChange={(e) => setNotifyOutcome(e.target.checked)}
          className="page-subscribe-popup__checkbox"
        />
        Game Outcome (Final Score)
      </label>

      <label className="page-subscribe-popup__option">
        <input 
          type="checkbox" 
          checked={notifyEvents}
          onChange={(e) => setNotifyEvents(e.target.checked)}
          className="page-subscribe-popup__checkbox"
        />
        Live Events (Tries, Cards, Kicks)
      </label>

      <div style={{ display: 'flex', gap: 'var(--space-2)' }}>
        {isSubscribed && (
          <button 
            onClick={handleUnsubscribe}
            className="btn btn--danger btn--sm page-subscribe-popup__btn"
          >
            Remove
          </button>
        )}
        <button 
          onClick={handleSaveSubscription}
          className="btn btn--primary btn--sm page-subscribe-popup__btn"
        >
          {isSubscribed ? 'Update' : 'Subscribe'}
        </button>
      </div>
    </div>
  )

  return (
    <div className="page-subscribe-container">
      <button
        ref={buttonRef}
        onClick={handleToggleClick}
        className={`page-subscribe-btn ${isSubscribed ? 'page-subscribe-btn--active' : ''}`}
        title={isSubscribed ? 'Manage match alerts' : 'Subscribe to match alerts'}
        disabled={loading}
      >
        <svg viewBox="0 0 24 24" width="18" height="18" fill={isSubscribed ? 'currentColor' : 'none'} stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9" />
          <path d="M13.73 21a2 2 0 0 1-3.46 0" />
        </svg>
      </button>

      {showPopup && (
        isMobile ? createPortal(popupContent, document.body) : popupContent
      )}
    </div>
  )
}
