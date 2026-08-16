import { CheckIcon } from "@/components/icons";

const operations = [
  { label: "add", value: "2", tone: "text-[#8ce8b3]" },
  { label: "keep", value: "187", tone: "text-[#d8dee9]" },
  { label: "move", value: "1", tone: "text-[#b4bfff]" },
  { label: "delete", value: "1", tone: "text-[#f0bd82]" },
] as const;

export function TerminalWindow() {
  return (
    <figure className="terminal-frame" aria-labelledby="terminal-caption">
      <div className="terminal-titlebar">
        <div className="flex items-center gap-1.5" aria-hidden="true">
          <span className="window-dot" />
          <span className="window-dot" />
          <span className="window-dot" />
        </div>
        <div className="terminal-title">steadlith / terminal</div>
        <div className="terminal-branch">main</div>
      </div>

      <div className="terminal-tabs" aria-hidden="true">
        <span className="terminal-tab terminal-tab-active">Plan</span>
        <span className="terminal-tab">Index</span>
        <span className="terminal-tab">Verify</span>
      </div>

      <div className="terminal-body">
        <div className="terminal-command">
          <span className="prompt">$</span> steadlith plan
        </div>

        <div className="plan-grid">
          <div>
            <div className="terminal-kicker">INDEX PLAN</div>
            <div className="operation-list">
              {operations.map((operation) => (
                <div className="operation-row" key={operation.label}>
                  <span className={operation.tone}>{operation.label}</span>
                  <span>{operation.value}</span>
                </div>
              ))}
            </div>
          </div>
          <div className="plan-summary">
            <div>
              <span>Embeddings</span>
              <strong>2 needed</strong>
            </div>
            <div>
              <span>Tokens</span>
              <strong>421</strong>
            </div>
            <div>
              <span>Provider price</span>
              <strong>unknown</strong>
            </div>
          </div>
        </div>

        <div className="terminal-rule" />

        <div className="terminal-command terminal-command-spaced">
          <span className="prompt">$</span> steadlith index --allow-delete
        </div>
        <div className="terminal-output">
          Applied <span>190 active</span>, embedded <span>2</span>, tombstoned <span>1</span>
        </div>

        <div className="terminal-command terminal-command-spaced">
          <span className="prompt">$</span> steadlith verify
        </div>
        <div className="verify-line">
          <span className="verify-icon">
            <CheckIcon className="h-3.5 w-3.5" />
          </span>
          Active index and manifest agree.
        </div>
      </div>

      <figcaption id="terminal-caption" className="terminal-caption">
        Illustrative CLI output. Counts depend on the corpus and configuration.
      </figcaption>
    </figure>
  );
}
