import { Lightbulb, CheckCircle2, Terminal, FolderOpen, Rocket, ArrowRight, Zap } from 'lucide-react'

export function HowToUse() {
  const steps = [
    {
      number: 1,
      title: 'Initialize Lloyd',
      description: 'Start by initializing Lloyd in your project directory. This creates a .lloyd folder with configuration files.',
      icon: FolderOpen,
      action: 'Go to Settings → Click "Initialize"',
      tip: 'You can also run `lloyd init` from the command line'
    },
    {
      number: 2,
      title: 'Submit Your Idea',
      description: 'Describe your product idea in plain English. Be specific about what you want to build. Lloyd will break it down into actionable tasks.',
      icon: Lightbulb,
      action: 'Go to New Idea → Describe your product → Submit',
      examples: [
        'Build a REST API with FastAPI that manages a todo list',
        'Create a CLI tool for converting images to different formats',
        'Build a web scraper that extracts product prices'
      ]
    },
    {
      number: 3,
      title: 'Watch Lloyd Work',
      description: 'Lloyd will decompose your idea into user stories, then execute them one by one. Watch the Live Preview on the Dashboard to see real-time progress.',
      icon: Zap,
      action: 'Monitor the Dashboard → Watch Live Preview',
      tip: 'Each task goes through planning, execution, and quality checks'
    },
    {
      number: 4,
      title: 'Review Tasks',
      description: 'Check the Tasks page to see all generated user stories, their status, and acceptance criteria. You can reset blocked tasks if needed.',
      icon: CheckCircle2,
      action: 'Go to Tasks → Review status → Reset if needed',
      tip: 'Tasks are prioritized automatically based on dependencies'
    },
    {
      number: 5,
      title: 'Test Your Product',
      description: 'Once Lloyd completes the tasks, your product is ready to test. Navigate to the output directory and run the generated code.',
      icon: Rocket,
      action: 'Navigate to output → Follow the generated README',
      commands: [
        { label: 'Python projects', cmd: 'uv run python main.py' },
        { label: 'Node.js projects', cmd: 'npm install && npm start' },
        { label: 'With tests', cmd: 'uv run pytest' }
      ]
    }
  ]

  return (
    <div className="animate-fade-in max-w-3xl">
      {/* Header */}
      <div className="mb-8">
        <p className="text-[var(--text-tertiary)] text-xs uppercase tracking-widest mb-1">Guide</p>
        <h2 className="text-2xl font-semibold text-[var(--text-primary)] tracking-tight">How to Use Lloyd</h2>
        <p className="text-sm text-[var(--text-secondary)] mt-2">
          From idea to working product in 5 steps
        </p>
      </div>

      {/* Steps */}
      <div className="space-y-4">
        {steps.map((step, index) => {
          const Icon = step.icon
          return (
            <div key={step.number} className="glass rounded-xl p-5 relative">
              {/* Connector line */}
              {index < steps.length - 1 && (
                <div className="absolute left-[2.35rem] top-[4.5rem] bottom-[-1rem] w-px bg-gradient-to-b from-accent-500/50 to-transparent" />
              )}

              <div className="flex gap-4">
                {/* Step number */}
                <div className="shrink-0">
                  <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-accent-500 to-accent-600 flex items-center justify-center text-white font-semibold text-sm glow">
                    {step.number}
                  </div>
                </div>

                {/* Content */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-2">
                    <Icon className="w-4 h-4 text-accent-400" />
                    <h3 className="font-medium text-[var(--text-primary)]">{step.title}</h3>
                  </div>

                  <p className="text-sm text-[var(--text-secondary)] mb-3">
                    {step.description}
                  </p>

                  {/* Action */}
                  <div className="flex items-center gap-2 text-xs text-accent-400 mb-3">
                    <ArrowRight className="w-3 h-3" />
                    <span>{step.action}</span>
                  </div>

                  {/* Examples */}
                  {step.examples && (
                    <div className="mt-3 p-3 bg-[var(--border-color)]/30 rounded-lg">
                      <p className="text-[10px] text-[var(--text-tertiary)] uppercase tracking-wider mb-2">Examples</p>
                      <ul className="space-y-1.5">
                        {step.examples.map((example, i) => (
                          <li key={i} className="text-xs text-[var(--text-secondary)] flex items-start gap-2">
                            <span className="text-accent-500 mt-0.5">•</span>
                            {example}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {/* Commands */}
                  {step.commands && (
                    <div className="mt-3 p-3 bg-[var(--border-color)]/30 rounded-lg">
                      <p className="text-[10px] text-[var(--text-tertiary)] uppercase tracking-wider mb-2">Commands</p>
                      <div className="space-y-2">
                        {step.commands.map((cmd, i) => (
                          <div key={i} className="flex items-center gap-3">
                            <span className="text-[10px] text-[var(--text-tertiary)] w-24 shrink-0">{cmd.label}</span>
                            <code className="text-xs text-accent-400 font-mono bg-[var(--bg-base)] px-2 py-1 rounded">
                              {cmd.cmd}
                            </code>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Tip */}
                  {step.tip && (
                    <div className="mt-3 flex items-start gap-2 text-xs text-[var(--text-tertiary)]">
                      <Terminal className="w-3 h-3 mt-0.5 shrink-0" />
                      <span>{step.tip}</span>
                    </div>
                  )}
                </div>
              </div>
            </div>
          )
        })}
      </div>

      {/* Quick Reference */}
      <div className="mt-8 glass rounded-xl p-5">
        <h3 className="font-medium text-[var(--text-primary)] mb-4">Quick Reference</h3>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <p className="text-[10px] text-[var(--text-tertiary)] uppercase tracking-wider mb-2">CLI Commands</p>
            <div className="space-y-1.5 font-mono text-xs">
              <div className="flex justify-between">
                <span className="text-[var(--text-secondary)]">lloyd init</span>
                <span className="text-[var(--text-tertiary)]">Initialize project</span>
              </div>
              <div className="flex justify-between">
                <span className="text-[var(--text-secondary)]">lloyd idea "..."</span>
                <span className="text-[var(--text-tertiary)]">Submit idea</span>
              </div>
              <div className="flex justify-between">
                <span className="text-[var(--text-secondary)]">lloyd status</span>
                <span className="text-[var(--text-tertiary)]">Check progress</span>
              </div>
              <div className="flex justify-between">
                <span className="text-[var(--text-secondary)]">lloyd resume</span>
                <span className="text-[var(--text-tertiary)]">Continue work</span>
              </div>
            </div>
          </div>

          <div>
            <p className="text-[10px] text-[var(--text-tertiary)] uppercase tracking-wider mb-2">Key Files</p>
            <div className="space-y-1.5 font-mono text-xs">
              <div className="flex justify-between">
                <span className="text-[var(--text-secondary)]">.lloyd/prd.json</span>
                <span className="text-[var(--text-tertiary)]">Task queue</span>
              </div>
              <div className="flex justify-between">
                <span className="text-[var(--text-secondary)]">.lloyd/progress.txt</span>
                <span className="text-[var(--text-tertiary)]">History log</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Tips */}
      <div className="mt-4 glass rounded-xl p-5 border-accent-500/20">
        <h3 className="font-medium text-[var(--text-primary)] mb-3 flex items-center gap-2">
          <Zap className="w-4 h-4 text-accent-400" />
          Pro Tips
        </h3>
        <ul className="space-y-2 text-sm text-[var(--text-secondary)]">
          <li className="flex items-start gap-2">
            <span className="text-accent-500">•</span>
            Be specific in your idea description - include tech stack preferences if you have any
          </li>
          <li className="flex items-start gap-2">
            <span className="text-accent-500">•</span>
            Start with smaller projects to understand how Lloyd works before tackling complex ones
          </li>
          <li className="flex items-start gap-2">
            <span className="text-accent-500">•</span>
            Use the "Dry run" option to preview the generated tasks without executing them
          </li>
          <li className="flex items-start gap-2">
            <span className="text-accent-500">•</span>
            Check the Progress page for detailed history and learnings from each session
          </li>
        </ul>
      </div>
    </div>
  )
}
