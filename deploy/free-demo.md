# Free temporary judge demo from the Mac

This is a short-lived alternative to renting a server. The same three-page
public pilot runs on the operator's Mac, and Cloudflare Quick Tunnel gives it
a temporary HTTPS URL. It is for a supervised hackathon demo, not an always-on
deployment. The Mac must stay awake and online. The URL changes after a restart;
there is no uptime guarantee.

The selected ASR remains Groq `whisper-large-v3`, not local Mac inference.
DeepL handles ordinary English/French translation, and ElevenLabs produces
optional speech. Provider free-tier quotas are separate from hosting. Do not
upgrade a provider account to a paid plan merely to run this demo. Anyone with
the temporary link can submit bounded work and use those quotas. Stop the
terminal when the judging window ends.

## Start

On the operator's Mac, install the free tunnel client once:

```sh
brew install cloudflared
```

From the repository root, run:

```sh
/usr/bin/caffeinate -i base-station/.venv/bin/python tools/run_free_demo.py
```

Or double-click `base-station/Open Moin Public Demo.command`. Both options keep
the Mac from idle sleeping while the demo runs. The command asks
for the Groq, DeepL, and ElevenLabs API keys in hidden terminal prompts unless
they are already in that terminal's environment. It does not save the keys or
put them on the command line, in Git, or in the browser. Enter them again after
a restart. Never send keys in chat or screenshots.

The command checks Groq first, before asking for DeepL and ElevenLabs keys. It
then checks the required tools, curated Qur'an rendering registry, and public
configuration before opening a tunnel. The Groq model lookup submits no audio.
HTTP 401 means the key was rejected; HTTP 403 can mean model permission is
blocked. A Cloudflare 1010 response is a request/network block, not a bad key.
If an old key is exported in the shell, run `unset GROQ_API_KEY` and restart.
The launcher waits until the Studio,
Haramain, and Live pages respond through the public URL, then opens the browser
and prints the link for the judges. Press Ctrl+C to stop both processes. The
temporary URL stops working and must not be submitted as a permanent link.
After the pages are reachable, the launcher also writes the temporary URL to
the ignored local file `base-station/studio-runs/public-demo/public-demo-url.txt`
so it can be checked without copying it from Terminal. It removes the file on
normal shutdown.
Cloudflare Tunnel requires outbound TCP or UDP port 7844. The current campus
network's connectivity check blocked both protocols; connect the Mac to an
iPhone hotspot or another network if the command reports that error.

This demo keeps recordings and the spend ledger under the Git-ignored
`base-station/studio-runs/` folder on the Mac. The same seven-day cleanup and
anonymous-pilot access limits apply. The local ledger uses conservative
planning reserves; it is not a provider billing control. Check that each
provider account remains on its free tier and monitor the provider dashboards.

Cloudflare Quick Tunnel does not support Server-Sent Events; Moin's current
live page uses ordinary HTTP polling. The tunnel has a 200 in-flight request
limit and no uptime guarantee. The less-than-ten-second text target and
50-listener capacity remain unverified over this route. See
https://developers.cloudflare.com/tunnel/get-started/quick-tunnels/ .
