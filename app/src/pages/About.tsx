import './About.css'

function About() {
  return (
    <div className="about">
      <div className="about-hero">
        <h2>About NCT Stats Ireland</h2>
        <p>Your source for National Car Test statistics and data across Ireland.</p>
      </div>

      <div className="about-grid">
        <div className="about-card">
          <h3>What is NCT Stats?</h3>
          <p>
            NCT Stats Ireland provides up-to-date statistics and trends on National Car Test
            results across Ireland, helping drivers make informed decisions about vehicle maintenance.
          </p>
        </div>

        <div className="about-card">
          <h3>What data do we show?</h3>
          <p>
            We provide pass/fail rates, common failure reasons, test centre statistics,
            and year-on-year trends broken down by vehicle make, model, and age.
          </p>
        </div>

        <div className="about-card">
          <h3>How to use the site</h3>
          <p>
            Use the <strong>Search</strong> page to look up statistics for a specific vehicle,
            or browse the <strong>Statistics</strong> page for nationwide trends and breakdowns.
          </p>
        </div>

        <div className="about-card">
          <h3>Download Data</h3>
          <p>
            Raw NCT data is available to download in CSV format from the
            <strong> Download</strong> page for your own analysis.
          </p>
        </div>
      </div>
    </div>
  )
}

export default About
