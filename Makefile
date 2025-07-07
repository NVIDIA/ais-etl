# Common setup for all stages
.PHONY: common_deps fmt-check fmt-fix help

SCRIPTS_DIR = ./scripts


common_deps: ## Install common Python dependencies for transformers
	cd transformers && make common_deps

fmt-deps: ## Install black and pylint for formatting and linting
	pip install --upgrade black[jupyter] pylint -q
	cd transformers && make common_deps

fmt-check: fmt-deps ## Check Python code formatting and linting
	@$(SHELL) "$(SCRIPTS_DIR)/bootstrap.sh" fmt
	@echo "✅ All formatting and linting checks passed successfully!"

fmt-fix: fmt-deps ## Fix Python code formatting automatically
	@$(SHELL) "$(SCRIPTS_DIR)/bootstrap.sh" fmt --fix

# Show help
help: ## Show this help message
	@echo "Usage:"
	@echo "  make [target]"
	@echo ""
	@echo "Available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'
	@echo ""
	@echo "Examples:"
	@printf "  \033[36m%s\033[0m\n    %s\n\n" \
		"make fmt-check" "Check Python code formatting and linting" \
		"make fmt-fix" "Fix Python code formatting automatically" \
		"make common_deps" "Install common Python dependencies for transformers" 