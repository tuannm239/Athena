import type { Preview } from "@storybook/react";
import "../app/globals.css";

const preview: Preview = {
  parameters: {
    backgrounds: { default: "athena", values: [{ name: "athena", value: "#0b0f19" }] },
    a11y: { test: "error" },
  },
};
export default preview;
