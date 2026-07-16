"use client";

import { useEffect, useRef, useState } from "react";
import Script from "next/script";
import { usePathname } from "next/navigation";
import {
  ANALYTICS_CONSENT_EVENT,
  hasAnalyticsConsent,
  isSensitiveAnalyticsPath,
} from "../utils/analytics";

const GA_ID = process.env.NEXT_PUBLIC_GA_ID || "";
const META_PIXEL_ID = process.env.NEXT_PUBLIC_META_PIXEL_ID || "";
const TIKTOK_PIXEL_ID = process.env.NEXT_PUBLIC_TIKTOK_PIXEL_ID || "";
const HAS_ANALYTICS_PROVIDER = Boolean(GA_ID || META_PIXEL_ID || TIKTOK_PIXEL_ID);
const ANALYTICS_READY_EVENT = "cealeg:analytics-ready";

function PageViewTracker() {
  const pathname = usePathname();
  const lastTrackedPathRef = useRef({ ga: "", meta: "", tiktok: "" });

  useEffect(() => {
    function trackPageView() {
      if (!hasAnalyticsConsent()) return;

      if (isSensitiveAnalyticsPath(pathname)) {
        lastTrackedPathRef.current = { ga: "", meta: "", tiktok: "" };
        return;
      }

      // Query strings may contain auth, checkout or user-provided data.
      if (GA_ID && window.gtag && lastTrackedPathRef.current.ga !== pathname) {
        window.gtag("event", "page_view", {
          page_location: `${window.location.origin}${pathname}`,
          page_path: pathname,
          page_title: document.title,
        });
        lastTrackedPathRef.current.ga = pathname;
      }

      if (META_PIXEL_ID && window.fbq && lastTrackedPathRef.current.meta !== pathname) {
        window.fbq("track", "PageView");
        lastTrackedPathRef.current.meta = pathname;
      }

      if (TIKTOK_PIXEL_ID && window.ttq && lastTrackedPathRef.current.tiktok !== pathname) {
        window.ttq.page();
        lastTrackedPathRef.current.tiktok = pathname;
      }
    }

    trackPageView();
    window.addEventListener(ANALYTICS_READY_EVENT, trackPageView);
    return () => window.removeEventListener(ANALYTICS_READY_EVENT, trackPageView);
  }, [pathname]);

  return null;
}

export function Analytics() {
  const [hasConsent, setHasConsent] = useState(false);

  useEffect(() => {
    function syncConsent() {
      setHasConsent(hasAnalyticsConsent());
    }

    syncConsent();
    window.addEventListener("storage", syncConsent);
    window.addEventListener(ANALYTICS_CONSENT_EVENT, syncConsent);

    return () => {
      window.removeEventListener("storage", syncConsent);
      window.removeEventListener(ANALYTICS_CONSENT_EVENT, syncConsent);
    };
  }, []);

  if (!HAS_ANALYTICS_PROVIDER || !hasConsent) {
    return null;
  }

  return (
    <>
      {GA_ID ? (
        <>
          <Script
            src={`https://www.googletagmanager.com/gtag/js?id=${GA_ID}`}
            strategy="afterInteractive"
          />
          <Script id="ga-init" strategy="afterInteractive">
            {`
              window.dataLayer = window.dataLayer || [];
              function gtag(){dataLayer.push(arguments);}
              window.gtag = gtag;
              gtag('js', new Date());
              gtag('consent', 'default', {
                analytics_storage: 'granted',
                ad_storage: 'granted',
                ad_user_data: 'granted',
                ad_personalization: 'granted'
              });
              gtag('config', '${GA_ID}', { send_page_view: false });
              window.dispatchEvent(new Event('${ANALYTICS_READY_EVENT}'));
            `}
          </Script>
        </>
      ) : null}
      {META_PIXEL_ID ? (
        <Script id="meta-pixel" strategy="afterInteractive">
          {`
            !function(f,b,e,v,n,t,s)
            {if(f.fbq)return;n=f.fbq=function(){n.callMethod?
            n.callMethod.apply(n,arguments):n.queue.push(arguments)};
            if(!f._fbq)f._fbq=n;n.push=n;n.loaded=!0;n.version='2.0';
            n.queue=[];t=b.createElement(e);t.async=!0;
            t.src=v;s=b.getElementsByTagName(e)[0];
            s.parentNode.insertBefore(t,s)}(window, document,'script',
            'https://connect.facebook.net/en_US/fbevents.js');
            fbq('init', '${META_PIXEL_ID}');
            window.dispatchEvent(new Event('${ANALYTICS_READY_EVENT}'));
          `}
        </Script>
      ) : null}
      {TIKTOK_PIXEL_ID ? (
        <Script id="tiktok-pixel" strategy="afterInteractive">
          {`
            !function (w, d, t) {
              w.TiktokAnalyticsObject = t;
              var ttq = w[t] = w[t] || [];
              ttq.methods = ['page','track','identify','instances','debug','on','off','once','ready','alias','group','enableCookie','disableCookie','holdConsent','revokeConsent','grantConsent'];
              ttq.setAndDefer = function(t,e){t[e]=function(){t.push([e].concat(Array.prototype.slice.call(arguments,0)))}};
              for (var i = 0; i < ttq.methods.length; i++) ttq.setAndDefer(ttq, ttq.methods[i]);
              ttq.instance = function(t){for (var e = ttq._i[t] || [], n = 0; n < ttq.methods.length; n++) ttq.setAndDefer(e, ttq.methods[n]); return e};
              ttq.load = function(e,n){var r='https://analytics.tiktok.com/i18n/pixel/events.js'; ttq._i=ttq._i||{}; ttq._i[e]=[]; ttq._i[e]._u=r; ttq._t=ttq._t||{}; ttq._t[e]=+new Date; ttq._o=ttq._o||{}; ttq._o[e]=n||{}; n=document.createElement('script'); n.type='text/javascript'; n.async=!0; n.src=r+'?sdkid='+e+'&lib='+t; e=document.getElementsByTagName('script')[0]; e.parentNode.insertBefore(n,e)};
              ttq.load('${TIKTOK_PIXEL_ID}');
              ttq.grantConsent();
              w.dispatchEvent(new Event('${ANALYTICS_READY_EVENT}'));
            }(window, document, 'ttq');
          `}
        </Script>
      ) : null}
      <PageViewTracker />
    </>
  );
}
