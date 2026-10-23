/** Telefon-Tastenfeld: Ziffer + Buchstaben wie auf dem Handy */
export const KEYPAD_KEYS = [
  { d: '1', l: '' }, { d: '2', l: 'ABC' }, { d: '3', l: 'DEF' },
  { d: '4', l: 'GHI' }, { d: '5', l: 'JKL' }, { d: '6', l: 'MNO' },
  { d: '7', l: 'PQRS' }, { d: '8', l: 'TUV' }, { d: '9', l: 'WXYZ' },
  { d: '*', l: '' }, { d: '0', l: '+' }, { d: '#', l: '' },
] as const

export const DTMF_RE = /^[0-9*#]$/
