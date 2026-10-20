# Course Chatbots

Custom-GPT-style chatbots that embed in Moodle. Each bot is a folder of text files in `bots/`, so there is no code to write per bot. Students sign in through Moodle, and nothing is saved.

**Start here: [HANDOFF.md](HANDOFF.md)**. It covers making a bot, embedding it in Moodle, troubleshooting and setup.

| Bot | Folder |
|---|---|
| DCJ820 Executive Policy Development Coach | `bots/dcj820-policy-coach-7rq2` |
| CDS244 Jordan Ellis, Senior Security Analyst | `bots/cds244-jordan-ellis-x8f3` |
| CEP505 Activity 2.1 Pre-Exercise Screening | `bots/cep505-screening-m5t1` |

Built with plain HTML/JS and one Vercel function that calls the OpenAI API. There are no dependencies, on purpose.
