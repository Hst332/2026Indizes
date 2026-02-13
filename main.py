from forecast_assets import run_all
from forecast_writer import write_daily_summary


def main():
    results = run_all()
    write_daily_summary(results)


if __name__ == "__main__":
    main()
