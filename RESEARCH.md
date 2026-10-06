# Research-informed HealthUp design — reviewed 6 October 2026

These sources informed design choices. They do not establish clinical efficacy for HealthUp, which has not undergone a clinical trial. Customer-facing summaries are brief, expandable, source-linked, and bundled for offline reading.

| Source | Finding and limitation | Implementation |
| --- | --- | --- |
| Wols et al., 2024, Clinical Psychology Review. [PMID 38320420](https://pubmed.ncbi.nlm.nih.gov/38320420/), DOI 10.1016/j.cpr.2024.102396 | Review of 145 randomized studies in people aged 6–24. Findings varied by game, population, and outcome; they do not validate a new game in all users. | Optional botanical matching puzzle. No leaderboard, countdown, diagnosis, or claim to treat stress. |
| Valentine et al., 2025, npj Digital Medicine. [PMID 40301581](https://pubmed.ncbi.nlm.nih.gov/40301581/), DOI 10.1038/s41746-025-01567-5 | Meta-analysis of 92 trials. No significant association between persuasive design principles and engagement or efficacy. Engagement definitions varied. | Useful tools, optional play, configurable reminders, no streak penalties, no forced progression. |
| 2026 Frontiers in Psychology review. [Full article](https://www.frontiersin.org/journals/psychology/articles/10.3389/fpsyg.2026.1745837/full), PMID 41878028, DOI 10.3389/fpsyg.2026.1745837 | Review of 30 internet-based CBT trials in college students. Findings concern structured, studied programs and cannot be transferred to HealthUp's wellness features. | Clear separation of self-care from therapy; Support provides real-world help instead of an AI therapist. |

## Product pattern research, not clinical evidence
- [Daylio mood statistics](https://daylio.net/faq/docs/daylio-faq/about/activity-and-mood-statistics/) informed clear mood counts and user-controlled history. HealthUp shows overlap observations without causal claims.
- [Headspace's explanation of online therapy](https://help.headspace.com/hc/en-us/articles/37969729073947-What-is-online-therapy-and-how-does-it-work) distinguishes licensed-professional sessions from wellness content. HealthUp does not advertise itself as therapy.
- [BuzzFeed's quiz directory](https://www.buzzfeed.com/quizzes) informed short preference choices only. Our three-question pause chooser is original and explicitly not a personality or clinical test.
- [Finch's official app listing](https://apps.apple.com/us/app/finch-self-care-pet/id1528595748) illustrates optional self-care tasks and reflection tools; product claims are not treated as independent clinical evidence.

## Support and medical information
US: [988 Lifeline](https://988lifeline.org/get-help/). Canada: [9-8-8](https://988.ca/). UK/Ireland: [Samaritans](https://www.samaritans.org/how-we-can-help/contact-samaritan/). Other countries: [Find a Helpline](https://findahelpline.com/). Immediate danger routes to local emergency services. HealthUp never monitors logs or automatically calls a service.

Nutrition estimates are generic bundled values, not live USDA measurements. [USDA API guide](https://fdc.nal.usda.gov/api-guide/) describes the server-side nutrient adapter. [NCBI usage guidelines](https://www.ncbi.nlm.nih.gov/books/NBK25497/) inform the PubMed adapter's conservative request pacing and caching.
