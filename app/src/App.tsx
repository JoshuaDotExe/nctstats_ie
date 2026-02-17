import Header from './components/Header'
import Navigation from './components/Navigation'
import './App.css'

function App() {
  return (
    <>
      <Header />
      <Navigation />
      <main>
        <h2>Welcome to NCT Stats Ireland</h2>
        <div className="card">
          <p>
            Start building your NCT statistics website here!
          </p>
        </div>
      </main>
    </>
  )
}

export default App
