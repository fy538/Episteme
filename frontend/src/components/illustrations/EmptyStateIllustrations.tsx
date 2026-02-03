/**
 * Empty State Illustrations
 * Custom SVG illustrations for empty states
 */

export function NoConversationsIllustration() {
  return (
    <svg
      className="w-48 h-48"
      viewBox="0 0 200 200"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
    >
      {/* Chat bubble */}
      <path
        d="M150 60H50C44.4772 60 40 64.4772 40 70V120C40 125.523 44.4772 130 50 130H70L85 145L100 130H150C155.523 130 160 125.523 160 120V70C160 64.4772 155.523 60 150 60Z"
        className="fill-accent-100 dark:fill-accent-900/30 stroke-accent-600 dark:stroke-accent-400"
        strokeWidth="2"
      />
      {/* Dots */}
      <circle cx="80" cy="95" r="6" className="fill-accent-400 dark:fill-accent-600" />
      <circle cx="100" cy="95" r="6" className="fill-accent-400 dark:fill-accent-600" />
      <circle cx="120" cy="95" r="6" className="fill-accent-400 dark:fill-accent-600" />
      {/* Sparkles */}
      <path
        d="M30 40L32 48L40 50L32 52L30 60L28 52L20 50L28 48L30 40Z"
        className="fill-accent-300 dark:fill-accent-700"
      />
      <path
        d="M170 100L171 105L176 106L171 107L170 112L169 107L164 106L169 105L170 100Z"
        className="fill-accent-300 dark:fill-accent-700"
      />
    </svg>
  );
}

export function NoCasesIllustration() {
  return (
    <svg
      className="w-48 h-48"
      viewBox="0 0 200 200"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
    >
      {/* Clipboard */}
      <rect
        x="50"
        y="30"
        width="100"
        height="140"
        rx="8"
        className="fill-neutral-100 dark:fill-neutral-800 stroke-neutral-400 dark:stroke-neutral-600"
        strokeWidth="2"
      />
      {/* Clip */}
      <rect
        x="80"
        y="20"
        width="40"
        height="20"
        rx="4"
        className="fill-accent-500 dark:fill-accent-600"
      />
      {/* Lines */}
      <line x1="70" y1="60" x2="130" y2="60" strokeWidth="3" className="stroke-neutral-300 dark:stroke-neutral-700" />
      <line x1="70" y1="80" x2="110" y2="80" strokeWidth="3" className="stroke-neutral-300 dark:stroke-neutral-700" />
      <line x1="70" y1="100" x2="120" y2="100" strokeWidth="3" className="stroke-neutral-300 dark:stroke-neutral-700" />
      {/* Checkmark */}
      <circle cx="100" cy="130" r="20" className="fill-success-100 dark:fill-success-900/30" />
      <path
        d="M92 130L98 136L108 124"
        stroke="currentColor"
        strokeWidth="3"
        strokeLinecap="round"
        strokeLinejoin="round"
        className="stroke-success-600 dark:stroke-success-400"
      />
    </svg>
  );
}

export function NoProjectsIllustration() {
  return (
    <svg
      className="w-48 h-48"
      viewBox="0 0 200 200"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
    >
      {/* Folder */}
      <path
        d="M40 60H90L100 70H160C165.523 70 170 74.4772 170 80V140C170 145.523 165.523 150 160 150H40C34.4772 150 30 145.523 30 140V70C30 64.4772 34.4772 60 40 60Z"
        className="fill-accent-100 dark:fill-accent-900/30 stroke-accent-600 dark:stroke-accent-400"
        strokeWidth="2"
      />
      {/* Plus sign */}
      <circle cx="100" cy="110" r="25" className="fill-white dark:fill-primary-950" />
      <line x1="100" y1="95" x2="100" y2="125" strokeWidth="4" className="stroke-accent-600 dark:stroke-accent-400" strokeLinecap="round" />
      <line x1="85" y1="110" x2="115" y2="110" strokeWidth="4" className="stroke-accent-600 dark:stroke-accent-400" strokeLinecap="round" />
    </svg>
  );
}

export function NoInquiriesIllustration() {
  return (
    <svg
      className="w-40 h-40"
      viewBox="0 0 160 160"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
    >
      {/* Magnifying glass */}
      <circle
        cx="70"
        cy="70"
        r="35"
        className="fill-warning-50 dark:fill-warning-900/20 stroke-warning-500 dark:stroke-warning-400"
        strokeWidth="4"
      />
      <line
        x1="95"
        y1="95"
        x2="120"
        y2="120"
        strokeWidth="8"
        strokeLinecap="round"
        className="stroke-warning-500 dark:stroke-warning-400"
      />
      {/* Question mark inside */}
      <path
        d="M70 55C70 50 73 48 76 48C79 48 82 50 82 54C82 57 80 58 78 60C76 62 75 63 75 66M75 74H75.01"
        stroke="currentColor"
        strokeWidth="3"
        strokeLinecap="round"
        className="stroke-warning-600 dark:stroke-warning-400"
      />
    </svg>
  );
}

export function NoSearchResultsIllustration() {
  return (
    <svg
      className="w-40 h-40"
      viewBox="0 0 160 160"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
    >
      {/* Magnifying glass */}
      <circle
        cx="70"
        cy="70"
        r="30"
        className="fill-neutral-100 dark:fill-neutral-800 stroke-neutral-400 dark:stroke-neutral-600"
        strokeWidth="3"
      />
      <line
        x1="92"
        y1="92"
        x2="115"
        y2="115"
        strokeWidth="6"
        strokeLinecap="round"
        className="stroke-neutral-400 dark:stroke-neutral-600"
      />
      {/* X mark inside */}
      <line x1="60" y1="60" x2="80" y2="80" strokeWidth="3" strokeLinecap="round" className="stroke-neutral-400 dark:stroke-neutral-600" />
      <line x1="80" y1="60" x2="60" y2="80" strokeWidth="3" strokeLinecap="round" className="stroke-neutral-400 dark:stroke-neutral-600" />
    </svg>
  );
}
