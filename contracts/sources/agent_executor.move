module agent_executor::agent_executor {
    use std::signer;
    use std::vector;
    use aptos_framework::fungible_asset::FungibleAsset;
    use aptos_framework::primary_fungible_store;
    use aptos_framework::account;
    use aptos_framework::event::{Self, EventHandle};
    use aptos_std::type_info;
    use uniswap_v2::pool;
    use uniswap_v2::factory;

    struct AgentExecutor has key {
        owner: address,
    }

    struct AgentExecutorEvents has key {
        trade_executed_events: EventHandle<TradeExecutedEvent>,
    }

    struct TradeExecutedEvent has drop, store {
        executor: address,
        token_x: type_info::TypeInfo,
        token_y: type_info::TypeInfo,
        direction: vector<u8>, // "X_TO_Y" or "Y_TO_X"
        amount_in: u64,
        amount_out: u64,
        tx_hash: vector<u8>,
    }

    struct ExecutionHistory has store, drop, copy {
        executor: address,
        token_x: type_info::TypeInfo,
        token_y: type_info::TypeInfo,
        direction: vector<u8>,
        amount_in: u64,
        amount_out: u64,
        timestamp: u64,
    }

    const E_NOT_OWNER: u64 = 1;
    const E_INVALID_DIRECTION: u64 = 2;
    const E_POOL_NOT_EXISTS: u64 = 3;
    const E_ZERO_AMOUNT: u64 = 4;

    public entry fun initialize(account: &signer) {
        let account_addr = signer::address_of(account);
        assert!(!exists<AgentExecutor>(account_addr), E_NOT_OWNER);

        move_to(account, AgentExecutor {
            owner: account_addr,
        });

        move_to(account, AgentExecutorEvents {
            trade_executed_events: account::new_event_handle<TradeExecutedEvent>(account),
        });
    }

    /// Execute a trade via Uniswap V2 pool
    /// direction: "X_TO_Y" or "Y_TO_X"
    public entry fun execute_agent_trade<X, Y>(
        account: &signer,
        direction: vector<u8>,
        amount_in: u64,
        min_amount_out: u64,
    ) acquires AgentExecutor, AgentExecutorEvents {
        let account_addr = signer::address_of(account);
        assert!(exists<AgentExecutor>(account_addr), E_NOT_OWNER);
        assert!(amount_in > 0, E_ZERO_AMOUNT);

        // Check if pool exists
        let pool_addr = factory::get_pool<X, Y>();
        assert!(pool_addr != @0x0, E_POOL_NOT_EXISTS);

        let executor_events = borrow_global_mut<AgentExecutorEvents>(account_addr);
        let timestamp = aptos_framework::timestamp::now_seconds();

        if (direction == b"X_TO_Y") {
            // Swap X for Y
            let metadata_x = get_token_metadata<X>();
            let asset_x = primary_fungible_store::withdraw(account, metadata_x, amount_in);
            
            let asset_y = pool::swap_x_to_y<X, Y>(account, asset_x, min_amount_out, account_addr);
            let amount_out = aptos_framework::fungible_asset::amount(&asset_y);
            
            primary_fungible_store::deposit(account_addr, asset_y);

            event::emit_event(&mut executor_events.trade_executed_events, TradeExecutedEvent {
                executor: account_addr,
                token_x: type_info::type_of<X>(),
                token_y: type_info::type_of<Y>(),
                direction: b"X_TO_Y",
                amount_in,
                amount_out,
                tx_hash: b"", // Will be set by transaction hash
            });
        } else if (direction == b"Y_TO_X") {
            // Swap Y for X
            let metadata_y = get_token_metadata<Y>();
            let asset_y = primary_fungible_store::withdraw(account, metadata_y, amount_in);
            
            let asset_x = pool::swap_y_to_x<X, Y>(account, asset_y, min_amount_out, account_addr);
            let amount_out = aptos_framework::fungible_asset::amount(&asset_x);
            
            primary_fungible_store::deposit(account_addr, asset_x);

            event::emit_event(&mut executor_events.trade_executed_events, TradeExecutedEvent {
                executor: account_addr,
                token_x: type_info::type_of<X>(),
                token_y: type_info::type_of<Y>(),
                direction: b"Y_TO_X",
                amount_in,
                amount_out,
                tx_hash: b"",
            });
        } else {
            abort E_INVALID_DIRECTION
        };
    }

    /// View function to get pool reserves
    #[view]
    public fun get_pool_reserves<X, Y>(): (u64, u64, u64) {
        pool::get_reserves<X, Y>()
    }

    /// View function to check if pool exists
    #[view]
    public fun pool_exists<X, Y>(): bool {
        let pool_addr = factory::get_pool<X, Y>();
        pool_addr != @0x0
    }

    fun get_token_metadata<T>(): aptos_framework::object::Object<aptos_framework::fungible_asset::Metadata> {
        // Get metadata from the token's module based on type name
        let type_name = type_info::struct_name(&type_info::type_of<T>());
        if (type_name == b"TokenA") {
            aptos_framework::object::address_to_object<aptos_framework::fungible_asset::Metadata>(
                aptos_framework::object::create_object_address(&@uniswap_v2, b"TokenA")
            )
        } else if (type_name == b"TokenB") {
            aptos_framework::object::address_to_object<aptos_framework::fungible_asset::Metadata>(
                aptos_framework::object::create_object_address(&@uniswap_v2, b"TokenB")
            )
        } else {
            // For any other token type, try to use the type name as the object seed
            aptos_framework::object::address_to_object<aptos_framework::fungible_asset::Metadata>(
                aptos_framework::object::create_object_address(&@uniswap_v2, type_name)
            )
        }
    }
}

