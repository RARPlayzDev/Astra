import { defineConfig } from "vitepress";

export default defineConfig({
  title: "ASTRA",
  description:
    "Adaptive Spectrum Threat Recognition & Analysis — Documentation",
  head: [
    ["link", { rel: "icon", href: "/astra_logo.svg" }],
    [
      "link",
      {
        rel: "stylesheet",
        href: "https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap",
      },
    ],
  ],
  themeConfig: {
    logo: "/astra_logo.svg",
    siteTitle: "ASTRA",
    nav: [
      { text: "Guide", link: "/guide/getting-started" },
      { text: "Concepts", link: "/concepts/problem-statement" },
      { text: "Reference", link: "/reference/api" },
      { text: "Tutorials", link: "/tutorials/first-mission" },
      { text: "Changelog", link: "/changelog" },
    ],
    sidebar: {
      "/guide/": [
        {
          text: "Getting Started",
          items: [
            { text: "Installation", link: "/guide/getting-started" },
            { text: "Quick Start", link: "/guide/quick-start" },
            { text: "Interface Tour", link: "/guide/interface-tour" },
          ],
        },
      ],
      "/concepts/": [
        {
          text: "Core Concepts",
          items: [
            { text: "The Problem", link: "/concepts/problem-statement" },
            {
              text: "SmartScan Algorithm",
              link: "/concepts/smartscan-algorithm",
            },
            {
              text: "Scheduling Policies",
              link: "/concepts/scheduling-policies",
            },
            {
              text: "Evaluation Methodology",
              link: "/concepts/evaluation-methodology",
            },
          ],
        },
      ],
      "/integration/": [
        {
          text: "Integration",
          items: [
            { text: "Radar & SDR", link: "/integration/radar-sdr" },
            { text: "Scenarios", link: "/integration/scenarios" },
            { text: "Datasets", link: "/integration/datasets" },
            {
              text: "Multi-Receiver",
              link: "/integration/multi-receiver",
            },
          ],
        },
      ],
      "/reference/": [
        {
          text: "Reference",
          items: [
            { text: "API Reference", link: "/reference/api" },
            { text: "CLI Tools", link: "/reference/cli" },
            { text: "File Formats", link: "/reference/file-formats" },
            { text: "Architecture", link: "/reference/architecture" },
          ],
        },
      ],
      "/tutorials/": [
        {
          text: "Tutorials",
          items: [
            { text: "First Mission", link: "/tutorials/first-mission" },
            {
              text: "Connecting Hardware",
              link: "/tutorials/connecting-hardware",
            },
            { text: "Training Models", link: "/tutorials/training-models" },
            { text: "Geolocation", link: "/tutorials/geolocation" },
          ],
        },
      ],
    },
    socialLinks: [
      { icon: "github", link: "https://github.com/smartscan-ew/astrea" },
    ],
    search: {
      provider: "local",
    },
    footer: {
      message: "Smart India Hackathon 2026 — Defence & Space",
      copyright: "ASTRA v1.0.0 · Simulation-based research software",
    },
    editLink: {
      pattern:
        "https://github.com/smartscan-ew/astrea/edit/main/docs/:path",
      text: "Edit this page on GitHub",
    },
  },
  lastUpdated: true,
  cleanUrls: true,
  markdown: {
    lineNumbers: true,
    theme: {
      light: "github-light",
      dark: "github-dark",
    },
  },
});
