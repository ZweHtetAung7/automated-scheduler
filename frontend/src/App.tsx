import { useEffect, useState } from 'react'

type ApiStatus = 'checking' | 'online' | 'offline'

function App() {
  const [apiStatus, setApiStatus] = useState<ApiStatus>('checking')

  useEffect(() => {
    fetch('/api/health')
      .then((res) => setApiStatus(res.ok ? 'online' : 'offline'))
      .catch(() => setApiStatus('offline'))
  }, [])

  return (
    <main>
      <h1>Automated Scheduler</h1>
      <p>Plans your day around classes, practice, deadlines, sleep and meals.</p>
      <p>
        Backend: <strong data-testid="api-status">{apiStatus}</strong>
      </p>
    </main>
  )
}

export default App
