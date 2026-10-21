import { ref } from 'vue'
import router from '@/router'
import { onMissedCall, usePresence, type MissedCallEvent } from '@/composables/usePresence'
import { useVoicemail } from '@/composables/useVoicemail'

export interface CallNotice extends MissedCallEvent {
  id: number
  name: string
}

const PREF_KEY = 'kitmunicator:notify:desktop'
const MAX_NOTICES = 3
const AUTO_HIDE_MS = 20_000

const notices = ref<CallNotice[]>([])
const desktopEnabled = ref(readPref())
const permission = ref<NotificationPermission | 'unsupported'>(
  'Notification' in window ? Notification.permission : 'unsupported',
)
let nextId = 1
let unsubscribe: (() => void) | null = null

function readPref(): boolean {
  try {
    return localStorage.getItem(PREF_KEY) !== 'off'
  } catch {
    return true
  }
}

/** Satz ohne den Namen – der wird im Toast hervorgehoben */
export function noticeSuffix(notice: CallNotice): string {
  return notice.voicemail_id ? 'hat angerufen und dir eine Voicemail hinterlassen' : 'hat angerufen'
}

export function noticeText(notice: CallNotice): string {
  return `${notice.name} ${noticeSuffix(notice)}`
}

export function useCallNotifications() {
  const { memberByExtension } = usePresence()
  const { load: loadVoicemail } = useVoicemail()

  function dismiss(id: number) {
    notices.value = notices.value.filter(n => n.id !== id)
  }

  function openVoicemail(notice: CallNotice) {
    dismiss(notice.id)
    router.push('/voicemail')
  }

  function showDesktop(notice: CallNotice) {
    // Nur wenn der Tab im Hintergrund ist — sonst reicht der Toast
    if (!document.hidden || !desktopEnabled.value || permission.value !== 'granted') return
    const n = new Notification(notice.voicemail_id ? 'Neue Voicemail' : 'Verpasster Anruf', {
      body: noticeText(notice),
      tag: `missed-${notice.at}`,
      icon: '/favicon.png',
    })
    n.onclick = () => {
      window.focus()
      if (notice.voicemail_id) openVoicemail(notice)
      n.close()
    }
  }

  function handle(event: MissedCallEvent) {
    const notice: CallNotice = {
      ...event,
      id: nextId++,
      name: event.caller_name || memberByExtension(event.caller_number)?.username || event.caller_number,
    }
    notices.value = [notice, ...notices.value].slice(0, MAX_NOTICES)
    setTimeout(() => dismiss(notice.id), AUTO_HIDE_MS)
    if (event.voicemail_id) loadVoicemail()
    showDesktop(notice)
  }

  /** Einmal in der App-Shell aufrufen */
  function start() {
    unsubscribe ??= onMissedCall(handle)
  }

  /** Muss aus einem Klick heraus kommen, sonst blockt der Browser die Abfrage */
  async function setDesktopEnabled(enabled: boolean) {
    if (enabled && permission.value === 'default') {
      permission.value = await Notification.requestPermission()
    }
    desktopEnabled.value = enabled
    try {
      localStorage.setItem(PREF_KEY, enabled ? 'on' : 'off')
    } catch {
      // Einstellung gilt dann nur für diese Sitzung
    }
  }

  return { notices, desktopEnabled, permission, start, dismiss, openVoicemail, setDesktopEnabled }
}
