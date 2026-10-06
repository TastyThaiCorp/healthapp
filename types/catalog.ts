/** Shared contract for future TypeScript clients and API integrations. */
export type ProductCategory = 'typescript' | 'python';
export interface ProductConcept {
  id: string;
  name: string;
  category: ProductCategory;
  focus: string;
  tagline: string;
  description: string;
  icon: string;
  image: number;
}
export interface Inquiry {
  name: string;
  email: string;
  interest: string;
  message: string;
  savedAt: string;
}
export interface IntegrationRequest {
  name: string;
  email: string;
  brief: string;
  interest: string;
  request_id: string;
  website: string;
}
export interface IntegrationReceipt {
  status: 'received';
  inquiry_id: string;
}
