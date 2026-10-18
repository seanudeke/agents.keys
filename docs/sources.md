# Implementation sources

Retrieved or checked on 2026-10-18. These sources support implementation semantics. They do not verify every reference in the supplied manuscript.

- GitHub REST search: https://docs.github.com/en/rest/search/search
- GitHub workflow syntax and permission inheritance: https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax
- Secure workflow use: https://docs.github.com/en/actions/reference/security/secure-use
- Safer checkout defaults, June 18, 2026: https://github.blog/changelog/2026-06-18-safer-pull_request_target-defaults-for-github-actions-checkout/
- Read-only untrusted-event caches, June 26, 2026: https://github.blog/changelog/2026-06-26-read-only-actions-cache-for-untrusted-triggers/
- Agentic Workflows architecture: https://github.blog/ai-and-ml/generative-ai/under-the-hood-security-architecture-of-github-agentic-workflows/
- Agents Rule of Two: https://ai.meta.com/blog/practical-ai-agent-security/
- IEEE author disclosure requirements: https://conferences.ieeeauthorcenter.ieee.org/author-ethics/guidelines-and-policies/submission-policies/

The catalog links canonical vendor repositories. Its CLI rules are intentionally narrow heuristics. Product-name matching alone is insufficient to establish an agent invocation.

CI pins were resolved from the official tag-reference endpoints:

- actions/checkout v6: d23441a48e516b6c34aea4fa41551a30e30af803
- actions/setup-python v6: ece7cb06caefa5fff74198d8649806c4678c61a1

Record future pin changes with their review date. A resolved upstream tag is not an independent security audit of the pinned code.
