import { useCallback, useEffect, useRef, useState } from 'react';
import { useLocation } from 'react-router-dom';
import { getHasPendingApiRequests, subscribeToApiActivity } from '../services/api';

const MIN_ROUTE_LOADER_MS = 240;
const ROUTE_LOADER_SETTLE_MS = 150;

export function GlobalLoader() {
  const location = useLocation();
  const [isVisible, setIsVisible] = useState(false);
  const isFirstRenderRef = useRef(true);
  const lastRouteRef = useRef(`${location.pathname}${location.search}`);
  const hideTimerRef = useRef<number | null>(null);
  const transitionRef = useRef({
    active: false,
    startedAt: 0,
    sawPendingRequest: false,
  });

  const clearHideTimer = useCallback(() => {
    if (hideTimerRef.current == null) {
      return;
    }

    window.clearTimeout(hideTimerRef.current);
    hideTimerRef.current = null;
  }, []);

  const scheduleHide = useCallback(() => {
    if (!transitionRef.current.active) {
      return;
    }

    if (getHasPendingApiRequests()) {
      return;
    }

    clearHideTimer();

    const elapsed = Date.now() - transitionRef.current.startedAt;
    const minimumDelay = Math.max(MIN_ROUTE_LOADER_MS - elapsed, 0);
    const settleDelay = transitionRef.current.sawPendingRequest ? 0 : ROUTE_LOADER_SETTLE_MS;

    hideTimerRef.current = window.setTimeout(() => {
      if (getHasPendingApiRequests()) {
        transitionRef.current.sawPendingRequest = true;
        return;
      }

      transitionRef.current.active = false;
      transitionRef.current.sawPendingRequest = false;
      setIsVisible(false);
      hideTimerRef.current = null;
    }, minimumDelay + settleDelay);
  }, [clearHideTimer]);

  useEffect(() => subscribeToApiActivity((hasPendingRequests) => {
    if (!transitionRef.current.active) {
      return;
    }

    if (hasPendingRequests) {
      transitionRef.current.sawPendingRequest = true;
      clearHideTimer();
      return;
    }

    scheduleHide();
  }), [clearHideTimer, scheduleHide]);

  useEffect(() => () => clearHideTimer(), [clearHideTimer]);

  useEffect(() => {
    const currentRoute = `${location.pathname}${location.search}`;

    if (isFirstRenderRef.current) {
      isFirstRenderRef.current = false;
      lastRouteRef.current = currentRoute;
      return;
    }

    if (currentRoute === lastRouteRef.current) {
      return;
    }

    lastRouteRef.current = currentRoute;
    transitionRef.current.active = true;
    transitionRef.current.startedAt = Date.now();
    transitionRef.current.sawPendingRequest = getHasPendingApiRequests();
    setIsVisible(true);
    scheduleHide();
  }, [location.pathname, location.search, scheduleHide]);

  return (
    <div id='loader' className={isVisible ? '' : 'loader-hidden'} aria-hidden={!isVisible}>
      <img src='/logo-loader.svg?v=20260504-2' alt='Caricamento Matchinn' className='loader-logo' />
    </div>
  );
}