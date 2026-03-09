-- Migration: Add performance history columns to fundperformance table
-- Date: 2026-03-09
-- Description: Adds JSON fields for storing historical performance data

-- Add quarterly_performance column (JSON array)
ALTER TABLE fundperformance ADD COLUMN quarterly_performance TEXT;

-- Add best_periods column (JSON object)
ALTER TABLE fundperformance ADD COLUMN best_periods TEXT;

-- Add worst_periods column (JSON object)
ALTER TABLE fundperformance ADD COLUMN worst_periods TEXT;

-- Add sip_returns column (JSON object)
ALTER TABLE fundperformance ADD COLUMN sip_returns TEXT;

-- Add cagr_cat_avg column (JSON object)
ALTER TABLE fundperformance ADD COLUMN cagr_cat_avg TEXT;
