import './Navigation.css'

interface NavigationProps {
  links?: { label: string; href: string }[]
}

function Navigation({ links }: NavigationProps) {
  const defaultLinks = [
    { label: 'Home', href: '#home' },
    { label: 'Statistics', href: '#stats' },
    { label: 'About', href: '#about' },
    { label: 'Contact', href: '#contact' }
  ]

  const navLinks = links || defaultLinks

  return (
    <nav className="navigation">
      {navLinks.map((link) => (
        <a key={link.href} href={link.href} className="nav-link">
          {link.label}
        </a>
      ))}
    </nav>
  )
}

export default Navigation
