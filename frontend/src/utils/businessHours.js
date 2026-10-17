export const dayDefinitions = [
  ['mon', 'Monday', 'Mon'],
  ['tue', 'Tuesday', 'Tue'],
  ['wed', 'Wednesday', 'Wed'],
  ['thu', 'Thursday', 'Thu'],
  ['fri', 'Friday', 'Fri'],
  ['sat', 'Saturday', 'Sat'],
  ['sun', 'Sunday', 'Sun']
]

export function defaultBusinessHours() {
  return dayDefinitions.map(([day]) => ({
    day,
    enabled: day !== 'sun',
    open: '09:00',
    close: '18:00'
  }))
}

export function normalizeBusinessHours(value) {
  const input = new Map((Array.isArray(value) ? value : []).map(item => [item?.day, item]))
  return defaultBusinessHours().map(defaultItem => {
    const item = input.get(defaultItem.day) || defaultItem
    return {
      day: defaultItem.day,
      enabled: item.enabled !== false,
      open: /^\d{2}:\d{2}$/.test(item.open || '') ? item.open : defaultItem.open,
      close: /^\d{2}:\d{2}$/.test(item.close || '') ? item.close : defaultItem.close
    }
  })
}

function dayRangeLabel(days) {
  if (!days.length) return ''
  const order = dayDefinitions.map(item => item[0])
  const short = Object.fromEntries(dayDefinitions.map(([id, , label]) => [id, label]))
  const indexes = days.map(day => order.indexOf(day))
  const contiguous = indexes.every((value, index) => index === 0 || value === indexes[index - 1] + 1)
  if (contiguous && days.length >= 3) return `${short[days[0]]}–${short[days.at(-1)]}`
  return days.map(day => short[day]).join(', ')
}

export function formatBusinessHours(value, timezone = 'UTC') {
  const schedule = normalizeBusinessHours(value)
  const groups = []
  let current = null

  for (const item of schedule) {
    if (!item.enabled) {
      current = null
      continue
    }
    const key = `${item.open}|${item.close}`
    if (current?.key === key) current.days.push(item.day)
    else {
      current = { key, open: item.open, close: item.close, days: [item.day] }
      groups.push(current)
    }
  }

  if (!groups.length) return 'Closed'
  const summary = groups.map(group => `${dayRangeLabel(group.days)} · ${group.open}–${group.close}`).join(' · ')
  return timezone ? `${summary} · ${timezone}` : summary
}

export function timeOptions(step = 15) {
  const values = []
  for (let hour = 0; hour < 24; hour += 1) {
    for (let minute = 0; minute < 60; minute += step) {
      values.push(`${String(hour).padStart(2, '0')}:${String(minute).padStart(2, '0')}`)
    }
  }
  return values
}
