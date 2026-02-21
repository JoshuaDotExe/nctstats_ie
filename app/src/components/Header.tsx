import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import './Header.css'

function Header() {
  const [menuOpen, setMenuOpen] = useState(false)

  useEffect(() => {
    const handleResize = () => {
      if (window.innerWidth > 768) {
        setMenuOpen(false)
      }
    }
    window.addEventListener('resize', handleResize)
    return () => window.removeEventListener('resize', handleResize)
  }, [])

  return (
    <header className="header">
      <div className="header-inner">
        <div className="header-brand">
          <h1>NCT Stats</h1>
        </div>

        <button
          className="header-hamburger"
          onClick={() => setMenuOpen(!menuOpen)}
          aria-label="Toggle menu"
          aria-expanded={menuOpen}
        >
          <span className={`hamburger-line ${menuOpen ? 'open' : ''}`} />
          <span className={`hamburger-line ${menuOpen ? 'open' : ''}`} />
          <span className={`hamburger-line ${menuOpen ? 'open' : ''}`} />
        </button>

        <nav className="header-nav">
          <Link to="/" className="header-nav-link" onClick={() => setMenuOpen(false)}>Home</Link>
          <Link to="/statistics" className="header-nav-link" onClick={() => setMenuOpen(false)}>Statistics</Link>
          <Link to="/search" className="header-nav-link" onClick={() => setMenuOpen(false)}>Search</Link>
          <Link to="/download" className="header-nav-link" onClick={() => setMenuOpen(false)}>Download</Link>
          <Link to="/about" className="header-nav-link" onClick={() => setMenuOpen(false)}>About</Link>
        </nav>
      </div>

      {menuOpen && (
        <nav className="header-dropdown">
          <Link to="/" className="header-dropdown-link" onClick={() => setMenuOpen(false)}>Home</Link>
          <Link to="/statistics" className="header-dropdown-link" onClick={() => setMenuOpen(false)}>Statistics</Link>
          <Link to="/search" className="header-dropdown-link" onClick={() => setMenuOpen(false)}>Search</Link>
          <Link to="/download" className="header-dropdown-link" onClick={() => setMenuOpen(false)}>Download</Link>
          <Link to="/about" className="header-dropdown-link" onClick={() => setMenuOpen(false)}>About</Link>
        </nav>
      )}
    </header>
  )
}

export default Header
