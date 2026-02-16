export const AGENTS = [
  {
    id: 'moderator',
    name: 'Diana Chen',
    role: 'Moderator',
    title: 'Chief of Staff',
    color: '#6366f1',
    avatar: 'DC',
    personality: 'Professional, warm but efficient. Manages the flow of the meeting.',
  },
  {
    id: 'skeptic',
    name: 'Marcus Webb',
    role: 'The Skeptic',
    title: 'CFO',
    color: '#ef4444',
    avatar: 'MW',
    personality: 'Challenges viability, questions ROI, pushes back on feasibility and assumptions.',
  },
  {
    id: 'analyst',
    name: 'Priya Sharma',
    role: 'The Analyst',
    title: 'VP of Strategy',
    color: '#10b981',
    avatar: 'PS',
    personality: 'Deep-dives into data, methodology, thoroughness. Wants evidence and rigor.',
  },
  {
    id: 'contrarian',
    name: "James O'Brien",
    role: 'The Contrarian',
    title: 'Board Advisor',
    color: '#f59e0b',
    avatar: 'JO',
    personality: 'Finds logical gaps, plays devil\'s advocate, explores worst-case scenarios.',
  },
];

export const INTERACTION_MODES = [
  {
    id: 'section',
    label: 'Section Breaks',
    desc: 'Agents hold questions until you finish each section',
    icon: '⏸',
  },
  {
    id: 'hand-raise',
    label: 'Hand Raise',
    desc: 'Agents raise hands; you choose when to take questions',
    icon: '✋',
  },
  {
    id: 'interrupt',
    label: 'Free Flow',
    desc: 'Agents can interject naturally, like a real boardroom',
    icon: '💬',
  },
];

export const INTENSITY_LEVELS = [
  { id: 'friendly', label: 'Friendly Dry Run', desc: 'Supportive, constructive feedback', emoji: '😊' },
  { id: 'moderate', label: 'Moderate Challenge', desc: 'Balanced pushback with support', emoji: '🤔' },
  { id: 'adversarial', label: 'Full Stress Test', desc: 'Aggressive, adversarial questioning', emoji: '🔥' },
];

export const FOCUS_AREAS = [
  'Financial Projections',
  'Go-to-Market Strategy',
  'Competitive Analysis',
  'Technical Feasibility',
  'Team & Execution',
  'Market Sizing',
  'Risk Assessment',
  'Timeline & Milestones',
];

export const SAMPLE_QUESTIONS = {
  skeptic: [
    "What's your contingency if these revenue projections fall short by 30%? I've seen optimistic models like this before.",
    "You're projecting 40% margins by year two — what specific evidence supports that given current market conditions?",
    'This assumes a favorable regulatory environment. What happens if the landscape shifts against us?',
    "I'm not convinced the TAM is as large as you're suggesting. How did you validate these numbers?",
  ],
  analyst: [
    'Can you walk me through the methodology behind your customer acquisition cost estimates?',
    "I'd like to see the sensitivity analysis on your key assumptions. What variables have the highest impact?",
    'Your competitive moat section mentions network effects — can you quantify the switching costs for customers?',
    "The data on slide 4 shows a trend, but the sample size seems small. What's your confidence interval?",
  ],
  contrarian: [
    "What if a major incumbent decides to enter this space with 10x your resources? What's your defense?",
    "You've presented the best case. Walk me through the scenario where everything goes wrong.",
    'This strategy assumes customers will change their behavior. History shows they rarely do. Why is this different?',
    "I see a fundamental tension between your growth targets and your profitability timeline. How do you reconcile that?",
  ],
  moderator: [
    "Thank you. Let's pause here — Marcus, I believe you had a question about the financials.",
    "Good point. Let's make sure we address that before moving on. Priya, your thoughts?",
    "We're about halfway through. Let's do a quick round of questions before continuing.",
    'I want to make sure we give enough time to the competitive analysis section. Let\'s move forward.',
  ],
};

export const DEMO_SLIDES = [
  {
    title: 'Executive Summary',
    subtitle: 'Q4 Strategic Initiative',
    bullets: ['Market opportunity overview', 'Proposed investment thesis', 'Expected ROI timeline'],
  },
  {
    title: 'Market Analysis',
    subtitle: 'Total Addressable Market',
    bullets: ['$4.2B global market by 2027', '18% CAGR in target segment', 'Key growth drivers identified'],
  },
  {
    title: 'Competitive Landscape',
    subtitle: 'Positioning & Differentiation',
    bullets: ['3 major incumbents analyzed', 'Our unique advantages', 'Defensible moat strategy'],
  },
  {
    title: 'Financial Projections',
    subtitle: '3-Year Model',
    bullets: ['Revenue: $12M → $45M → $120M', 'Gross margin: 65% → 72%', 'Break-even: Month 18'],
  },
  {
    title: 'Go-to-Market',
    subtitle: 'Launch Strategy',
    bullets: ['Phase 1: Enterprise pilots', 'Phase 2: Mid-market expansion', 'Phase 3: Self-serve platform'],
  },
  {
    title: 'Team & Ask',
    subtitle: 'Investment Request',
    bullets: ['$15M Series A raise', 'Key hires planned', '18-month runway'],
  },
];
