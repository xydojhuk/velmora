// This is a neutral offline shell, not catalog data. The backend is the only
// authority for product names, pricing, stock and checkout availability.
export const storeInfo = {
  name: 'Velmora',
  tagline: 'Your online store',
  footerDescription: 'A self-hosted storefront.',
  phoneDisplay: '',
  phoneHref: '',
  email: '',
  hours: '',
  timezone: 'UTC',
  location: '',
  warranty: 'Contact the store for warranty details.',
  warrantyNote: 'The seller provides the applicable warranty terms.'
}

export const fallbackProducts = []
export function fallbackProduct() { return null }
