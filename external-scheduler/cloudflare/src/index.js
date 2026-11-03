// External Gold V5 scheduling trigger. Does not calculate signals or place orders.
// Configure GITHUB_WORKFLOW_TOKEN as a Cloudflare Worker secret (never commit it).
const OWNER = "ReneGold";
const REPO = "gold-signal-bot";
const WORKFLOW = "gold-v5-forward-paper.yml";

export default {
  async fetch() {
    return new Response("Gold V5 trigger: scheduled-only; no public dispatch endpoint.", {status: 404});
  },
  async scheduled(controller, env) {
    if (!env.GITHUB_WORKFLOW_TOKEN) {
      throw new Error("GITHUB_WORKFLOW_TOKEN is not configured");
    }
    const url = `https://api.github.com/repos/${OWNER}/${REPO}/actions/workflows/${WORKFLOW}/dispatches`;
    const resp = await fetch(url, {
      method: "POST",
      headers: {
        "Accept": "application/vnd.github+json",
        "Authorization": `Bearer ${env.GITHUB_WORKFLOW_TOKEN}`,
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "gold-v5-external-cron"
      },
      body: JSON.stringify({ref: "main"})
    });
    if (resp.status !== 204) {
      // Intentionally do not print GitHub response bodies or tokens.
      throw new Error(`GitHub dispatch rejected: HTTP ${resp.status}`);
    }
    console.log("Gold V5 paper workflow dispatch accepted", {
      scheduledUTC: new Date(controller.scheduledTime).toISOString(),
      // 204 only confirms accepted dispatch, not successful job execution.
      dispatchAccepted: true
    });
  }
};
