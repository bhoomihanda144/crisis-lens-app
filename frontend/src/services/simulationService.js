import { api } from './api'
import { isDemo } from './mode'
import * as mock from './mockApi'

export const runSimulation = (scenario) => (isDemo() ? mock.runSimulation(scenario) : api.post('/simulate', scenario))