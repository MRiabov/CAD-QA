import { Highlight, themes } from "prism-react-renderer";
import type { Language } from "prism-react-renderer";

export function Code({ code, language }: { code: string; language: Language }) {
  return (
    <Highlight theme={themes.github} code={code.trimEnd()} language={language}>
      {({ tokens, getLineProps, getTokenProps }) => (
        <pre className="code">
          {tokens.map((line, index) => (
            <div {...getLineProps({ line })} key={index}>
              {line.map((token, tokenIndex) => (
                <span {...getTokenProps({ token })} key={tokenIndex} />
              ))}
            </div>
          ))}
        </pre>
      )}
    </Highlight>
  );
}
