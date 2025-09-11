async function runMalcolmOptimizer() {
  const info = {
    userAgent: navigator.userAgent,
    cores: navigator.hardwareConcurrency,
    memory: navigator.deviceMemory || "unknown",
    connection: navigator.connection ? navigator.connection.downlink + " Mbps" : "unknown"
  };

  try {
    const response = await fetch("/optimize", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(info)
    });

    const suggestions = await response.json();

    const output = document.getElementById("malcolm-optimizer");
    output.innerHTML = `
      <h3>🔧 Malcolm’s Recommendations</h3>
      <ul>
        ${suggestions.recommendations.map(r => `<li>${r}</li>`).join("")}
      </ul>
    `;
  } catch (err) {
    console.error("Optimizer error:", err);
  }
}

document.addEventListener("DOMContentLoaded", runMalcolmOptimizer);
