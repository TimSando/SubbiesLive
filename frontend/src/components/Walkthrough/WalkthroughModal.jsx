import { useState, useEffect } from 'react';
import './WalkthroughModal.css';

const WALKTHROUGH_STEPS = [
  {
    title: 'Your Personalised Dashboard',
    desc: 'Welcome to SubbiesStats! The home page gives you a snapshot of live, upcoming and recent games',
    image: '/assets/walkthrough/step1-dashboard.png'
  },
  {
    title: 'Never Miss a Try',
    desc: 'Enable push notifications to receive instant score updates directly to your device. Look out for the flashing Live indicator to follow games as they happen!',
    image: '/assets/walkthrough/step2-live.png'
  },
  {
    title: 'Dive Deep into the Numbers',
    desc: 'Debating who the best kicker in the league is? Head to the Stats page to see comprehensive player and club leaderboards. Toggle between Total season points and Per-Game Averages.',
    image: '/assets/walkthrough/step3-stats.png'
  },
  {
    title: 'Explore Sydney rugby',
    desc: "Browse all Sydney Rugby club by division or find those with active women's teams. Get a view of their homeground, training schedule and social media profiles.",
    image: '/assets/walkthrough/step4-clubs.png'
  },
  {
    title: 'For the Whistleblowers',
    desc: 'Are you an official? Log in securely via RugbyXplorer in the RefZone to view your past and upcoming appointments, track match statuses, and see your co-officials all in one place.',
    image: '/assets/walkthrough/step5-refzone.png'
  }
];

export default function WalkthroughModal() {
  const [isOpen, setIsOpen] = useState(false);
  const [currentStep, setCurrentStep] = useState(0);
  const [isFadingOut, setIsFadingOut] = useState(false);

  useEffect(() => {
    const hasSeenTour = localStorage.getItem('subbies_walkthrough_completed');
    if (!hasSeenTour) {
      setIsOpen(true);
    }
  }, []);

  const closeTour = () => {
    setIsFadingOut(true);
    setTimeout(() => {
      setIsOpen(false);
      localStorage.setItem('subbies_walkthrough_completed', 'true');
    }, 300);
  };

  const nextStep = () => {
    if (currentStep < WALKTHROUGH_STEPS.length - 1) {
      setCurrentStep(prev => prev + 1);
    } else {
      closeTour();
    }
  };

  if (!isOpen) return null;

  const stepData = WALKTHROUGH_STEPS[currentStep];
  const isLastStep = currentStep === WALKTHROUGH_STEPS.length - 1;

  return (
    <div className={`walkthrough-overlay ${isFadingOut ? 'walkthrough-overlay--fade-out' : ''}`}>
      <div className="walkthrough-modal card">
        <div className="walkthrough-modal__image-container">
          <img src={stepData.image} alt={stepData.title} className="walkthrough-modal__image" />
        </div>

        <div className="walkthrough-modal__content">
          <h2 className="walkthrough-modal__title">{stepData.title}</h2>
          <p className="walkthrough-modal__desc">{stepData.desc}</p>
        </div>

        <div className="walkthrough-modal__footer">
          <div className="walkthrough-modal__dots">
            {WALKTHROUGH_STEPS.map((_, index) => (
              <span
                key={index}
                className={`walkthrough-dot ${index === currentStep ? 'walkthrough-dot--active' : ''}`}
              />
            ))}
          </div>

          <div className="walkthrough-modal__actions">
            <button className="btn btn--ghost" onClick={closeTour}>Skip</button>
            <button className="btn btn--primary" onClick={nextStep}>
              {isLastStep ? 'Get Started' : 'Next'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
