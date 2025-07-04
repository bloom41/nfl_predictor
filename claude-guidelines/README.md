# 🎯 Claude Development Guidelines

Modular guideline files for efficient Claude collaboration on the NFL Predictor project.

## 📁 Guidelines Structure

Load only the context Claude needs per task to save tokens and improve relevance:

```
claude-guidelines/
├── claude-guidelines-core.md        # 🎯 Core development philosophy
├── claude-guidelines-frontend.md    # 🖥️ React TypeScript standards
├── claude-guidelines-backend.md     # 🚀 Express API guidelines
├── claude-guidelines-ml.md          # 🤖 ML service standards
├── claude-guidelines-database.md    # 🗄️ Database layer rules
├── claude-guidelines-testing.md     # 🔍 Testing practices
├── claude-guidelines-devops.md      # ⚙️ CI/CD & deployment
└── claude-guidelines-integrations.md # 🔗 Service communication
```

## 🚀 Usage Instructions

### For Core Development
Load: `claude-guidelines-core.md` (always include)

### For Frontend Work
Load: `claude-guidelines-core.md` + `claude-guidelines-frontend.md`

### For Backend API Work
Load: `claude-guidelines-core.md` + `claude-guidelines-backend.md`

### For ML Pipeline Work
Load: `claude-guidelines-core.md` + `claude-guidelines-ml.md`

### For Database Changes
Load: `claude-guidelines-core.md` + `claude-guidelines-database.md`

### For Testing Implementation
Load: `claude-guidelines-core.md` + `claude-guidelines-testing.md`

### For DevOps/Deployment
Load: `claude-guidelines-core.md` + `claude-guidelines-devops.md`

### For Service Integration
Load: `claude-guidelines-core.md` + `claude-guidelines-integrations.md`

## 🎯 Benefits

- **Token Efficiency**: Load only relevant context
- **Focused Guidance**: Specific standards per domain
- **Consistent Quality**: Unified development approach
- **Modular Design**: Easy to update individual guidelines

## 📝 Maintenance

- Update individual files as project evolves
- Keep guidelines lean and actionable
- Include examples and anti-patterns
- Review quarterly for relevance

---

_Created: July 2025 • Author: Hogan • Project: NFL Predictor_