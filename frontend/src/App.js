import React, { useState } from "react";
import "./App.css";

// 🔥 Update API Base URL to Railway backend (NO TRAILING SLASH)
const API_BASE_URL = "const API_BASE_URL = "https://cryptointelai-production.up.railway.app/"; // ✅ Correct Railway URL
";  // ✅ Update this

function App() {
  const [query, setQuery] = useState("");
  const [reportType, setReportType] = useState("free");
  const [email, setEmail] = useState("");
  const [loading, setLoading] = useState(false);
  const [responseMessage, setResponseMessage] = useState("");

  // ✅ Test Connection to Backend
  const testBackendConnection = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/test`);
      const result = await response.json();
      alert(`✅ Backend Response: ${result.message}`);
    } catch (error) {
      alert(`❌ Backend Connection Failed: ${error.message}`);
    }
  };

  // 🔹 Function to send API request
  const handleSubmit = async (event) => {
    event.preventDefault();
    setLoading(true);
    setResponseMessage("");

    const requestBody = {
      research_query: query,
      report_type: reportType,
      email: reportType === "free" ? email : undefined,
    };

    try {
      const response = await fetch(`${API_BASE_URL}/submit-query`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(requestBody),
      });

      const result = await response.json();
      if (response.ok) {
        setResponseMessage(`✅ Request received: ${JSON.stringify(result)}`);
      } else {
        setResponseMessage(`❌ Error: ${result.detail || "Something went wrong"}`);
      }
    } catch (error) {
      setResponseMessage(`❌ Request failed: ${error.message}`);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="App">
      <header className="App-header">
        <h1>CryptoIntel AI</h1>
        <p>Get AI-generated research on any cryptocurrency topic.</p>

        {/* ✅ New Button to Test Backend Connection */}
        <button onClick={testBackendConnection}>Test Backend Connection</button>

        <form onSubmit={handleSubmit}>
          <label>
            Enter Your Research Topic:
            <input type="text" value={query} onChange={(e) => setQuery(e.target.value)} required />
          </label>

          <label>
            Select Report Type:
            <select value={reportType} onChange={(e) => setReportType(e.target.value)}>
              <option value="free">Free Report</option>
              <option value="basic">Advanced Research Report ($29)</option>
              <option value="deep">Deep Research Report ($99)</option>
            </select>
          </label>

          {reportType === "free" && (
            <label>
              Enter Your Email (Required for Free Reports):
              <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
            </label>
          )}

          <button type="submit" disabled={loading}>
            {loading ? "Processing..." : "Get Research Report"}
          </button>
        </form>

        {responseMessage && <p>{responseMessage}</p>}
      </header>
    </div>
  );
}

export default App;
