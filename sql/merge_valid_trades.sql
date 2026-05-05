MERGE `{{ project_id }}.{{ dataset }}.valid_trades` AS target
USING `{{ project_id }}.{{ dataset }}.valid_trades_staging` AS source
ON target.trade_id = source.trade_id
WHEN MATCHED AND source.version >= target.version THEN
  UPDATE SET
    portfolio = source.portfolio,
    counterparty = source.counterparty,
    instrument = source.instrument,
    quantity = source.quantity,
    price = source.price,
    version = source.version,
    trade_date = source.trade_date,
    maturity_date = source.maturity_date,
    updated_at = source.updated_at,
    status = source.status
WHEN NOT MATCHED THEN
  INSERT (
    trade_id,
    portfolio,
    counterparty,
    instrument,
    quantity,
    price,
    version,
    trade_date,
    maturity_date,
    updated_at,
    status
  )
  VALUES (
    source.trade_id,
    source.portfolio,
    source.counterparty,
    source.instrument,
    source.quantity,
    source.price,
    source.version,
    source.trade_date,
    source.maturity_date,
    source.updated_at,
    source.status
  );
