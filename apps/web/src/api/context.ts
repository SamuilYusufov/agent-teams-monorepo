import { createApiClient, type ApiClient } from '@agent-team/api-client'
import { createContext, useContext } from 'react'

export const ApiContext = createContext<ApiClient>(createApiClient())

/** The API client of the nearest `ApiProvider`. */
export function useApi(): ApiClient {
  return useContext(ApiContext)
}
