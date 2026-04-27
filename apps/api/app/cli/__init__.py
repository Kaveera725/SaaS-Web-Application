import click

from app.extensions import db
from app.models.billing import Plan, PlanName


def register_cli(app):
	@app.cli.command("seed")
	def seed():
		default_plans = [
			{
				"name": PlanName.FREE,
				"price_monthly": 0,
				"stripe_price_id": None,
				"features": {
					"projects": 1,
					"members": 1,
					"priority_support": False,
				},
			},
			{
				"name": PlanName.PRO,
				"price_monthly": 29,
				"stripe_price_id": None,
				"features": {
					"projects": 50,
					"members": 10,
					"priority_support": True,
				},
			},
			{
				"name": PlanName.ENTERPRISE,
				"price_monthly": 99,
				"stripe_price_id": None,
				"features": {
					"projects": -1,
					"members": -1,
					"priority_support": True,
				},
			},
		]

		inserted = 0
		for plan_data in default_plans:
			existing_plan = Plan.query.filter_by(name=plan_data["name"]).first()
			if existing_plan:
				continue

			db.session.add(Plan(**plan_data))
			inserted += 1

		db.session.commit()
		click.echo(f"Seed completed. Inserted {inserted} plan(s).")
