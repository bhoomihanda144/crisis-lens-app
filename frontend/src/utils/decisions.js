export const DECISIONS = [
  { value: 'referred_to_duty_officer', title: 'Refer to duty officer', hint: 'A responder with authority will decide on dispatch.', needsNote: false },
  { value: 'monitoring', title: 'Keep monitoring', hint: 'Watch for new reports before deciding.', needsNote: false },
  { value: 'dismissed', title: 'Dismiss this recommendation', hint: 'You judge that no action is needed now.', needsNote: true },
]

export const DECISION_LABEL = {
  not_decided: 'No human decision yet',
  referred_to_duty_officer: 'Referred to duty officer',
  monitoring: 'Monitoring',
  dismissed: 'Recommendation dismissed',
}