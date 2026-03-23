import {
  useState,
  useRef,
  useEffect,
  useId,
  type KeyboardEvent,
  type ChangeEvent,
} from 'react'
import './Combobox.css'

interface ComboboxProps {
  id?: string
  label: string
  value: string
  onChange: (value: string) => void
  options: string[]
  placeholder?: string
  required?: boolean
  disabled?: boolean
}

/** Highlight the matched portion of an option */
function Highlighted({ text, query }: { text: string; query: string }) {
  if (!query) return <>{text}</>
  const idx = text.toUpperCase().indexOf(query.toUpperCase())
  if (idx === -1) return <>{text}</>
  return (
    <>
      {text.slice(0, idx)}
      <mark>{text.slice(idx, idx + query.length)}</mark>
      {text.slice(idx + query.length)}
    </>
  )
}

export default function Combobox({
  id,
  label,
  value,
  onChange,
  options,
  placeholder,
  required,
  disabled,
}: ComboboxProps) {
  const autoId = useId()
  const inputId = id ?? autoId
  const listId = `${inputId}-list`

  const [open, setOpen] = useState(false)
  const [activeIdx, setActiveIdx] = useState(-1)
  const inputRef = useRef<HTMLInputElement>(null)
  const listRef = useRef<HTMLUListElement>(null)
  const containerRef = useRef<HTMLDivElement>(null)

  // Filter options to those containing the typed text
  const filtered = options.filter((o) =>
    o.toUpperCase().includes(value.trim().toUpperCase()),
  )

  // Close on outside click
  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setOpen(false)
        setActiveIdx(-1)
      }
    }
    document.addEventListener('mousedown', handleClick)
    return () => document.removeEventListener('mousedown', handleClick)
  }, [])

  // Scroll active item into view
  useEffect(() => {
    if (activeIdx >= 0 && listRef.current) {
      const item = listRef.current.children[activeIdx] as HTMLElement | undefined
      item?.scrollIntoView({ block: 'nearest' })
    }
  }, [activeIdx])

  function handleInput(e: ChangeEvent<HTMLInputElement>) {
    onChange(e.target.value)
    setOpen(true)
    setActiveIdx(-1)
  }

  function handleSelect(option: string) {
    onChange(option)
    setOpen(false)
    setActiveIdx(-1)
    inputRef.current?.focus()
  }

  function handleKeyDown(e: KeyboardEvent<HTMLInputElement>) {
    if (!open) {
      if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
        setOpen(true)
        setActiveIdx(0)
        e.preventDefault()
      }
      return
    }

    switch (e.key) {
      case 'ArrowDown':
        setActiveIdx((i) => Math.min(i + 1, filtered.length - 1))
        e.preventDefault()
        break
      case 'ArrowUp':
        setActiveIdx((i) => Math.max(i - 1, 0))
        e.preventDefault()
        break
      case 'Enter':
        if (activeIdx >= 0 && filtered[activeIdx]) {
          handleSelect(filtered[activeIdx])
          e.preventDefault()
        }
        break
      case 'Escape':
        setOpen(false)
        setActiveIdx(-1)
        break
      case 'Tab':
        setOpen(false)
        setActiveIdx(-1)
        break
    }
  }

  const showList = open && filtered.length > 0

  return (
    <div className="combobox-field" ref={containerRef}>
      <label htmlFor={inputId}>{label}</label>
      <div className="combobox-input-wrap">
        <input
          ref={inputRef}
          id={inputId}
          type="text"
          role="combobox"
          autoComplete="off"
          aria-autocomplete="list"
          aria-expanded={showList}
          aria-controls={listId}
          aria-activedescendant={activeIdx >= 0 ? `${listId}-${activeIdx}` : undefined}
          value={value}
          placeholder={placeholder}
          required={required}
          disabled={disabled}
          onChange={handleInput}
          onFocus={() => { if (value || options.length > 0) setOpen(true) }}
          onKeyDown={handleKeyDown}
        />
        {value && (
          <button
            type="button"
            className="combobox-clear"
            aria-label="Clear"
            tabIndex={-1}
            onClick={() => { onChange(''); setOpen(true); inputRef.current?.focus() }}
          >
            ×
          </button>
        )}
      </div>

      {showList && (
        <ul
          ref={listRef}
          id={listId}
          role="listbox"
          className="combobox-list"
        >
          {filtered.map((option, idx) => (
            <li
              key={option}
              id={`${listId}-${idx}`}
              role="option"
              aria-selected={idx === activeIdx}
              className={`combobox-option${idx === activeIdx ? ' active' : ''}`}
              onMouseDown={() => handleSelect(option)}
              onMouseEnter={() => setActiveIdx(idx)}
            >
              <Highlighted text={option} query={value} />
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
