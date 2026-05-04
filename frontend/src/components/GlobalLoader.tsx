import { useEffect, useState } from 'react';
import { getHasPendingApiRequests, subscribeToApiActivity } from '../services/api';

export function GlobalLoader() {
  const [isVisible, setIsVisible] = useState(getHasPendingApiRequests());

  useEffect(() => subscribeToApiActivity(setIsVisible), []);

  return (
    <div id='loader' className={isVisible ? '' : 'loader-hidden'} aria-hidden={!isVisible}>
      <img src='/logo-loader.svg' alt='Caricamento Matchinn' className='loader-logo' />
    </div>
  );
}