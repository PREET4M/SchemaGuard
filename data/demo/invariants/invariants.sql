-- Invariant 1: No negative order totals
SELECT id FROM orders WHERE total < 0;

-- Invariant 2: No orphaned orders
SELECT o.id FROM orders o LEFT JOIN users u ON o.user_id = u.id WHERE u.id IS NULL;

