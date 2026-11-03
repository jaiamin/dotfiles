return {
  {
    "folke/tokyonight.nvim",
    opts = {
      style = "night",
      light_style = "day",
      transparent = false,
      on_colors = function(colors)
        if vim.o.background == "dark" then
          colors.bg = "#000000"
          colors.bg_dark = "#000000"
          colors.bg_sidebar = "#000000"
          colors.bg_float = "#000000"
        end
      end,
    },
  },
  {
    "LazyVim/LazyVim",
    opts = {
      colorscheme = "tokyonight",
    },
  },
}
